"""用户列表接口（GET /users）测试。

守三件事：
1. 权限：ADMIN/MANAGER 可用，OPERATOR 被拒（403 FORBIDDEN）
2. 安全：响应里绝不能出现 password_hash
3. 功能：分页 + keyword 过滤
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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_list_users_admin_ok(client):
    """ADMIN 能拿列表，字段齐全且含 status。"""
    token = await _login(client)
    resp = await client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["total"] >= 3, "种子至少 3 个账号"
    first = body["items"][0]
    assert set(first) == {"id", "username", "display_name", "role", "status"}


async def test_list_users_never_exposes_password_hash(client):
    """安全红线：任何情况下响应体不得含 password_hash / 密码哈希字符串。"""
    token = await _login(client)
    resp = await client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 200
    raw = resp.text
    assert "password_hash" not in raw
    assert "$2b$" not in raw, "bcrypt 哈希前缀不能出现在响应里"


async def test_list_users_operator_forbidden(client):
    """OPERATOR 无权查看用户名单。"""
    token = await _login(client, "op01", "op123")
    resp = await client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


async def test_list_users_manager_allowed(client):
    """MANAGER 也可以看（现场约定主管能管基础数据）。"""
    token = await _login(client, "sup01", "sup123")
    resp = await client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 200


async def test_list_users_keyword_filter(client):
    """keyword 对 username 模糊搜。"""
    token = await _login(client)
    resp = await client.get(
        "/api/v1/users", params={"keyword": "sup"}, headers=_auth(token)
    )
    assert resp.status_code == 200
    usernames = [i["username"] for i in resp.json()["items"]]
    assert "sup01" in usernames
    assert "admin" not in usernames


async def test_list_users_role_filter(client):
    """role 精确过滤。"""
    token = await _login(client)
    resp = await client.get(
        "/api/v1/users", params={"role": "ADMIN"}, headers=_auth(token)
    )
    assert resp.status_code == 200
    assert all(i["role"] == "ADMIN" for i in resp.json()["items"])


async def test_list_users_requires_auth(client):
    """未登录 401。"""
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401
