"""P1 第 4 批测试：商品增改 + AI 接口占位。

重点：
  - 商品写接口的错误码对不对（409 编码重复 / 404 不存在 / 422 参数）
  - exclude_unset 语义：不传保持原值、传 null 才清空
  - 一条业务保护：有库存的商品不能改成批次管理
  - AI 接口返回 501 而不是 404
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.main import app


@pytest.fixture
async def client(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def clean_test_skus(session):
    """清理测试创建的商品（sku_code 以 TEST- 开头）。"""
    yield
    await session.execute(text("delete from sku where sku_code like 'TEST-%'"))
    await session.commit()


@pytest.fixture
async def clean_stock(session):
    """清空库存，用于「有库存」相关测试。"""
    await session.execute(
        text(
            "TRUNCATE stock_txn, inventory, inbound_order, outbound_order "
            "RESTART IDENTITY CASCADE"
        )
    )
    await session.commit()
    yield


async def _login(client, username="admin", password="admin123"):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 新建商品
# ---------------------------------------------------------------------------
async def test_create_sku(client, clean_test_skus):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/skus",
        json={
            "sku_code": "TEST-0001",
            "name": "测试商品A",
            "barcode": "6900000000001",
            "spec": "1*10",
            "category": "测试",
            "base_uom": "BOX",
            "is_batch_managed": True,
            "safety_stock": 10,
            "reorder_point": 30,
            "abc_class": "B",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["sku_code"] == "TEST-0001"
    assert d["name"] == "测试商品A"
    assert d["is_batch_managed"] is True
    assert d["safety_stock"] == 10
    assert d["abc_class"] == "B"
    # 默认值生效
    assert d["status"] == 1


async def test_create_sku_defaults(client, clean_test_skus):
    """只给必填字段时，其余取默认值。"""
    token = await _login(client)
    resp = await client.post(
        "/api/v1/skus",
        json={"sku_code": "TEST-0002", "name": "最小商品"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["base_uom"] == "EA"
    assert d["is_batch_managed"] is False
    assert d["safety_stock"] == 0


async def test_create_sku_duplicate_code(client, clean_test_skus):
    token = await _login(client)
    body = {"sku_code": "TEST-0003", "name": "重复编码"}
    first = await client.post("/api/v1/skus", json=body, headers=_auth(token))
    assert first.status_code == 201

    second = await client.post("/api/v1/skus", json=body, headers=_auth(token))
    assert second.status_code == 409
    err = second.json()
    assert err["code"] == "SKU_CODE_EXISTS"
    assert err["detail"]["sku_code"] == "TEST-0003"


async def test_create_sku_missing_name(client):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/skus", json={"sku_code": "TEST-0004"}, headers=_auth(token)
    )
    assert resp.status_code == 422


async def test_create_sku_invalid_abc(client):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/skus",
        json={"sku_code": "TEST-0005", "name": "x", "abc_class": "Z"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 修改商品
# ---------------------------------------------------------------------------
async def test_update_sku_single_field(client, clean_test_skus):
    """只改一个字段，其余保持不变（exclude_unset 语义）。"""
    token = await _login(client)
    created = await client.post(
        "/api/v1/skus",
        json={
            "sku_code": "TEST-0010",
            "name": "原名",
            "spec": "原规格",
            "safety_stock": 5,
        },
        headers=_auth(token),
    )
    sku_id = created.json()["id"]

    resp = await client.put(
        f"/api/v1/skus/{sku_id}",
        json={"name": "新名"},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["name"] == "新名"
    # 未传的字段保持原值
    assert d["spec"] == "原规格"
    assert d["safety_stock"] == 5


async def test_update_sku_clear_nullable(client, clean_test_skus):
    """显式传 null 才清空 —— 和「不传」是两件事。"""
    token = await _login(client)
    created = await client.post(
        "/api/v1/skus",
        json={"sku_code": "TEST-0011", "name": "有规格", "spec": "待清空"},
        headers=_auth(token),
    )
    sku_id = created.json()["id"]

    resp = await client.put(
        f"/api/v1/skus/{sku_id}",
        json={"spec": None},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["spec"] is None


async def test_update_sku_not_found(client):
    token = await _login(client)
    resp = await client.put(
        "/api/v1/skus/999999", json={"name": "x"}, headers=_auth(token)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def test_update_sku_batch_flag_blocked_with_stock(client, session, clean_stock):
    """有库存的商品不能从「非批次管理」改成「批次管理」。

    SKU-1002（抽纸）是 is_batch_managed=false，先给它造库存，再尝试改。
    改了会让历史库存变成「批次管理商品但没有批次号」，批次追溯直接断链。
    """
    token = await _login(client)

    sku_id = (
        await session.execute(text("select id from sku where sku_code = 'SKU-1002'"))
    ).scalar_one()
    loc_id = (
        await session.execute(
            text("select id from location where location_code = 'WH01-A-01-01-01'")
        )
    ).scalar_one()

    await session.execute(
        text(
            "insert into inventory (sku_id, location_id, batch_no, expiry_date, "
            "qty_on_hand, qty_allocated) "
            "values (:s, :l, '', date '9999-12-30', 50, 0)"
        ),
        {"s": sku_id, "l": loc_id},
    )
    await session.execute(
        text(
            "insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no, "
            "expiry_date, on_hand_delta, allocated_delta, before_on_hand, "
            "after_on_hand, source) "
            "values ('TEST-SEED-1002', 'RECEIPT', :s, :l, '', date '9999-12-30', "
            "50, 0, 0, 50, 'IMPORT')"
        ),
        {"s": sku_id, "l": loc_id},
    )
    await session.commit()

    resp = await client.put(
        f"/api/v1/skus/{sku_id}",
        json={"is_batch_managed": True},
        headers=_auth(token),
    )
    assert resp.status_code == 409
    err = resp.json()
    assert err["code"] == "SKU_BATCH_FLAG_CONFLICT"
    assert err["detail"]["qty_on_hand"] == 50


async def test_update_sku_batch_flag_allowed_without_stock(client, session, clean_stock):
    """没有库存时允许改批次管理标记。"""
    token = await _login(client)

    sku_id = (
        await session.execute(text("select id from sku where sku_code = 'SKU-1002'"))
    ).scalar_one()

    resp = await client.put(
        f"/api/v1/skus/{sku_id}",
        json={"is_batch_managed": True},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_batch_managed"] is True

    # 还原，避免影响其他测试
    await session.execute(
        text("update sku set is_batch_managed = false where id = :s"), {"s": sku_id}
    )
    await session.commit()


# ---------------------------------------------------------------------------
# AI 接口占位
# ---------------------------------------------------------------------------
async def test_agent_query_returns_501(client):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/agent/queries",
        json={"query": "3 号库 A 区还有多少矿泉水"},
        headers=_auth(token),
    )
    assert resp.status_code == 501
    err = resp.json()
    assert err["code"] == "NOT_IMPLEMENTED"
    assert err["detail"]["planned"] == "P2 · W7-W8"


async def test_agent_suggestion_returns_501(client):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/agent/suggestions",
        headers={**_auth(token), "X-Agent-Run-Id": "run-xyz"},
    )
    assert resp.status_code == 501
    assert resp.json()["code"] == "NOT_IMPLEMENTED"


async def test_agent_approve_returns_501(client):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/agent/suggestions/1/approve", headers=_auth(token)
    )
    assert resp.status_code == 501
    assert resp.json()["code"] == "NOT_IMPLEMENTED"


async def test_agent_requires_auth(client):
    """AI 接口也需要认证 —— 不能让未登录的人探测内部能力。"""
    resp = await client.post("/api/v1/agent/queries", json={"query": "test"})
    assert resp.status_code == 401
