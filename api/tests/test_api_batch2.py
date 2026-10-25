"""P1 第 2 批接口测试：入库单 / 出库单 CRUD。

覆盖：建单（头+明细）、详情、列表、改明细（仅 DRAFT）、取消（状态机校验）。
收货/上架/分配/拣货/发运属第 3 批，这里不测。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client, username="admin", password="admin123"):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _get_sku_ids(client, token):
    resp = await client.get("/api/v1/skus", headers={"Authorization": f"Bearer {token}"})
    items = resp.json()["items"]
    return [i["id"] for i in items]


# ---------------------------------------------------------------------------
# 入库单
# ---------------------------------------------------------------------------
async def test_create_inbound_order(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    resp = await client.post(
        "/api/v1/inbound-orders",
        json={
            "order_type": "PO",
            "supplier_name": "测试供应商",
            "lines": [
                {"sku_id": sku_ids[0], "qty_required": 100},
                {"sku_id": sku_ids[1], "qty_required": 50},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["order_no"].startswith("IN-")
    assert data["total_expected_qty"] == 150
    assert len(data["lines"]) == 2
    # 明细里带出 sku_code/sku_name
    assert all("sku_code" in line for line in data["lines"])
    assert data["lines"][0]["line_no"] == 1


async def test_create_inbound_order_empty_lines(client):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_create_inbound_order_bad_sku(client):
    token = await _login(client)
    resp = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": 999999, "qty_required": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_get_inbound_order(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_ids[0], "qty_required": 10}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = created.json()["id"]

    resp = await client.get(
        f"/api/v1/inbound-orders/{order_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id
    assert len(resp.json()["lines"]) == 1


async def test_get_inbound_order_not_found(client):
    token = await _login(client)
    resp = await client.get(
        "/api/v1/inbound-orders/999999", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


async def test_update_inbound_line_draft(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_ids[0], "qty_required": 10}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = created.json()["id"]
    line_id = created.json()["lines"][0]["id"]

    resp = await client.patch(
        f"/api/v1/inbound-orders/{order_id}/lines/{line_id}",
        json={"qty_required": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["qty_required"] == 30

    # 头部汇总同步更新
    detail = await client.get(
        f"/api/v1/inbound-orders/{order_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert detail.json()["total_expected_qty"] == 30


async def test_cancel_inbound_order_draft(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_ids[0], "qty_required": 10}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = created.json()["id"]

    resp = await client.post(
        f"/api/v1/inbound-orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


async def test_cancel_inbound_order_twice_conflict(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_ids[0], "qty_required": 10}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = created.json()["id"]

    await client.post(
        f"/api/v1/inbound-orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        f"/api/v1/inbound-orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 出库单
# ---------------------------------------------------------------------------
async def test_create_outbound_order(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    resp = await client.post(
        "/api/v1/outbound-orders",
        json={
            "order_type": "SALE",
            "customer_name": "测试客户",
            "priority": 50,
            "lines": [{"sku_id": sku_ids[0], "qty_required": 20}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["order_no"].startswith("OUT-")
    assert data["total_qty"] == 20
    assert data["priority"] == 50
    assert len(data["lines"]) == 1


async def test_get_outbound_order(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    created = await client.post(
        "/api/v1/outbound-orders",
        json={"order_type": "SALE", "lines": [{"sku_id": sku_ids[0], "qty_required": 5}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = created.json()["id"]

    resp = await client.get(
        f"/api/v1/outbound-orders/{order_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


async def test_cancel_outbound_order_draft(client):
    token = await _login(client)
    sku_ids = await _get_sku_ids(client, token)
    created = await client.post(
        "/api/v1/outbound-orders",
        json={"order_type": "SALE", "lines": [{"sku_id": sku_ids[0], "qty_required": 5}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = created.json()["id"]

    resp = await client.post(
        f"/api/v1/outbound-orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


async def test_list_inbound_orders(client):
    token = await _login(client)
    resp = await client.get(
        "/api/v1/inbound-orders", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert "items" in resp.json()
    assert "meta" in resp.json()


async def test_list_outbound_orders(client):
    token = await _login(client)
    resp = await client.get(
        "/api/v1/outbound-orders", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert "items" in resp.json()
    assert "meta" in resp.json()
