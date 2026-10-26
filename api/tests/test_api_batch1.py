"""P1 第 1 批接口测试：认证 / 主数据 / 库存读。

验证这些接口能正确工作，且与契约的响应结构一致。
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.main import app


@pytest.fixture
async def client(session):
    """异步测试客户端（真实连库）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client, username="admin", password="admin123"):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------
async def test_login_ok(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert resp.status_code == 401


async def test_me_requires_token(client):
    # 无 token 应 401
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_with_token(client):
    token = await _login(client)
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "ADMIN"


# ---------------------------------------------------------------------------
# 主数据
# ---------------------------------------------------------------------------
async def test_list_skus(client):
    token = await _login(client)
    resp = await client.get("/api/v1/skus", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "meta" in data
    assert data["meta"]["total"] >= 3  # 种子有 3 个 SKU


async def test_get_sku(client):
    token = await _login(client)
    resp = await client.get("/api/v1/skus", headers={"Authorization": f"Bearer {token}"})
    sku_id = resp.json()["items"][0]["id"]
    resp2 = await client.get(f"/api/v1/skus/{sku_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["id"] == sku_id


async def test_list_locations(client):
    token = await _login(client)
    resp = await client.get("/api/v1/locations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


# ---------------------------------------------------------------------------
# 库存读
# ---------------------------------------------------------------------------
async def test_list_inventory(client):
    """库存查询接口：结构与字段正确即可。

    刻意不断言「至少有一条库存」—— 库存是测试过程中会被其他用例
    TRUNCATE 又重建的可变状态，让本用例依赖它会让测试之间产生顺序耦合，
    换一个执行顺序就红。库存内容正确性由第 3 批的全链路测试保证。
    """
    token = await _login(client)
    resp = await client.get("/api/v1/inventory", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)
    assert {"total", "page", "page_size"} <= set(data["meta"])
    # 有数据时校验字段完整（没数据也算通过）
    for item in data["items"]:
        assert {"sku_code", "location_code", "qty_on_hand", "qty_available"} <= set(item)


async def test_list_stock_txn(client):
    token = await _login(client)
    resp = await client.get("/api/v1/stock-txn", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_recon_requires_manager(client):
    token = await _login(client, "op01", "op123")  # OPERATOR 无权限
    resp = await client.get("/api/v1/inventory/recon", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_recon_manager(client):
    token = await _login(client, "sup01", "sup123")  # MANAGER 有权限
    resp = await client.get("/api/v1/inventory/recon", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_recon_item_includes_codes(client):
    """对账项必须带 sku_code / location_code。

    对账页要显示「哪个商品在哪个库位不平」。只给 sku_id / location_id 的话，
    前端得自己拿两个列表 join，join 不到时还没法排查（而这正是对账最需要的能力）。
    """
    token = await _login(client, "sup01", "sup123")
    resp = await client.get(
        "/api/v1/inventory/recon", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items, "种子数据应至少有一条对账记录"
    for it in items:
        assert "sku_code" in it, "对账项缺 sku_code"
        assert "location_code" in it, "对账项缺 location_code"
    # 种子期初库存是 200 件在 A0101，必然存在这条
    assert any(it["sku_code"] == "SKU-1001" and it["location_code"] == "A0101" for it in items)


async def test_inventory_item_includes_spec(client, session):
    """库存项必须带 spec（规格）。

    B 联调反馈：库存查询页想显示规格，但 InventoryItem 里没这个字段，
    只能显示编码 + 名称。契约只增字段、不改语义，老调用方不受影响。

    走真实链路造数（建单 -> 收货 -> 查库存），顺带覆盖「收货后立刻可查」
    这条前端最依赖的路径。
    """
    token = await _login(client)
    auth = {"Authorization": f"Bearer {token}"}
    sku_id = (
        await session.execute(text("select id from sku where sku_code = 'SKU-1001'"))
    ).scalar_one()
    batch = "SPEC-" + uuid.uuid4().hex[:8]

    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_id, "qty_required": 5}]},
        headers=auth,
    )
    assert created.status_code == 201, created.text
    order = created.json()

    recv = await client.post(
        f"/api/v1/inbound-orders/{order['id']}/receive",
        json={
            "lines": [
                {
                    "line_id": order["lines"][0]["id"],
                    "qty_actual": 5,
                    "batch_no": batch,
                    "expiry_date": "2027-06-30",
                }
            ]
        },
        headers=auth,
    )
    assert recv.status_code == 200, recv.text

    resp = await client.get(f"/api/v1/inventory?batch_no={batch}", headers=auth)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items, "刚收的货应该立刻能查到库存"
    item = items[0]
    assert "spec" in item, f"InventoryItem 缺 spec 字段，实际字段: {sorted(item)}"
    assert item["spec"] == "550ml*24/箱"
    # 顺带确认基础字段没被这次改动影响
    assert item["sku_code"] == "SKU-1001"
    assert item["qty_on_hand"] == 5
