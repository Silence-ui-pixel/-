"""错误响应格式一致性测试（B 联调反馈驱动）。

背景：契约（contracts/openapi.yaml 的 Error schema）规定所有错误响应统一为
    { "code": "UNAUTHORIZED", "message": "...", "detail": {...} }

但首轮联调发现：只有 DomainError 那条链路走对了，FastAPI 内置的
HTTPException / RequestValidationError 仍返回默认的 { "detail": "..." }。
前端拿不到 code，就没法按错误类型分流（缺货弹明细、失效状态提示刷新、
token 过期自动跳登录）。

这组测试就是「契约的可执行版本」——任何人再往路由里抛裸 HTTPException，
格式都会被这里守住。

对照关系（B 实测的 6 个场景）：
    1 登录密码错      401  -> UNAUTHORIZED
    2 未带 token      401  -> UNAUTHORIZED
    3 权限不足        403  -> FORBIDDEN
    4 单据不存在      404  -> NOT_FOUND
    5 建单缺 lines    422  -> VALIDATION_ERROR（detail.errors 结构化）
    6 库存不足        409  -> INVENTORY_INSUFFICIENT（对照组，原本就对）
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

API = "/api/v1"


@pytest.fixture
async def client(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _assert_error_shape(body: dict) -> None:
    """每个错误响应都必须满足的最小契约。"""
    assert set(body) >= {"code", "message"}, f"缺少 code/message: {body}"
    assert isinstance(body["code"], str) and body["code"], "code 必须是非空字符串"
    assert isinstance(body["message"], str) and body["message"], "message 必须是非空字符串"
    # detail 在契约里是 object（不是 null）——前端可以直接点取字段而不用判空
    assert "detail" in body, "缺少 detail（契约要求存在，无附加信息时给空对象）"
    assert isinstance(body["detail"], dict), f"detail 必须是 object，实际: {type(body['detail'])}"


async def _login(client, username="admin", password="admin123") -> str:
    resp = await client.post(
        f"{API}/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# 场景 1：登录密码错 -> 401 UNAUTHORIZED
# ---------------------------------------------------------------------------
async def test_login_wrong_password_returns_unauthorized_code(client):
    resp = await client.post(
        f"{API}/auth/login", json={"username": "admin", "password": "definitely-wrong"}
    )
    assert resp.status_code == 401
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "UNAUTHORIZED"
    # 中文提示必须保留：前端直接展示 message，不该让人看到英文
    assert "密码" in body["message"]


# ---------------------------------------------------------------------------
# 场景 2：未带 token -> 401 UNAUTHORIZED
# ---------------------------------------------------------------------------
async def test_missing_token_returns_unauthorized_code(client):
    resp = await client.get(f"{API}/users/me")
    assert resp.status_code == 401
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "UNAUTHORIZED"


async def test_invalid_token_returns_unauthorized_code(client):
    """token 乱填也要走同一套结构（前端据此清本地 token 跳登录）。"""
    resp = await client.get(
        f"{API}/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# 场景 3：权限不足 -> 403 FORBIDDEN
# ---------------------------------------------------------------------------
async def test_forbidden_returns_forbidden_code(client):
    """OPERATOR 角色查对账（需要 MANAGER）——403 必须带 FORBIDDEN。"""
    token = await _login(client, username="op01", password="op123")
    resp = await client.get(
        f"{API}/inventory/recon", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 场景 4：资源不存在 -> 404 NOT_FOUND
# ---------------------------------------------------------------------------
async def test_not_found_returns_not_found_code(client):
    token = await _login(client)
    resp = await client.get(
        f"{API}/inbound-orders/999999", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "NOT_FOUND"
    assert "入库单" in body["message"]


# ---------------------------------------------------------------------------
# 场景 5：请求体校验失败 -> 422 VALIDATION_ERROR + 字段级 detail
# ---------------------------------------------------------------------------
async def test_validation_error_is_structured(client):
    """缺 body 必填字段时，前端要能指出「哪个字段错了」。

    这里刻意断言 detail.errors 里能拿到字段路径（loc），
    否则前端只能显示一句「参数不合法」，等于没说。
    """
    token = await _login(client)
    resp = await client.post(
        f"{API}/inbound-orders",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "err-fmt-001"},
        json={},  # 空 body，缺所有必填
    )
    assert resp.status_code == 422
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "VALIDATION_ERROR"
    errors = body["detail"]["errors"]
    assert isinstance(errors, list) and errors, "必须有字段级错误列表"
    first = errors[0]
    assert "loc" in first and "msg" in first
    # loc 要是 list（Pydantic v2 里可能是 tuple，JSON 化后必须是 list）
    assert isinstance(first["loc"], list)
    # 整段必须能 JSON 序列化（曾因 ctx 里塞了 ValueError 对象导致 500）
    assert isinstance(first["msg"], str)


# ---------------------------------------------------------------------------
# 场景 6：对照组 —— 业务错误本来就对，不能被这次改动弄坏
# ---------------------------------------------------------------------------
async def test_domain_error_shape_unchanged(client, clean_tables, base_ids):
    """库存不足仍应是 INVENTORY_INSUFFICIENT + 完整 detail。"""
    token = await _login(client)

    # 建一个超量出库单
    resp = await client.post(
        f"{API}/outbound-orders",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "err-fmt-002"},
        json={
            "lines": [{"sku_id": base_ids["sku_id"], "qty_required": 999999}],
        },
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()

    resp = await client.post(
        f"{API}/outbound-orders/{order['id']}/allocate",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "err-fmt-003"},
    )
    assert resp.status_code == 409
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "INVENTORY_INSUFFICIENT"
    # 关键字段一个都不能少，前端要拿来做缺货明细展示
    for key in ("sku_code", "batch_no", "required", "available", "shortfall"):
        assert key in body["detail"], f"INVENTORY_INSUFFICIENT.detail 缺 {key}"


# ---------------------------------------------------------------------------
# 兜底：未在映射表里的状态码也要有 code，不能退化成 {detail}
# ---------------------------------------------------------------------------
async def test_unmapped_status_still_has_code(client):
    """405 Method Not Allowed 属于 StarletteHTTPException，同样要转格式。"""
    resp = await client.request("DELETE", f"{API}/health")
    assert resp.status_code == 405
    body = resp.json()
    _assert_error_shape(body)
    assert body["code"] == "METHOD_NOT_ALLOWED"
