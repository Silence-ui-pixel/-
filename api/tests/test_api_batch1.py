"""P1 第 1 批接口测试：认证 / 主数据 / 库存读。

验证这些接口能正确工作，且与契约的响应结构一致。
"""

import pytest
from httpx import ASGITransport, AsyncClient

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
    token = await _login(client)
    resp = await client.get("/api/v1/inventory", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # 种子数据里有 1 条期初库存
    assert data["meta"]["total"] >= 1


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
