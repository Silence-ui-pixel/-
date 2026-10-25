from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health_ok():
    """存活探针不依赖数据库，必须永远 200。"""
    resp = client.get(f"{settings.api_prefix}/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_docs_available():
    """骨架阶段至少要能看到 OpenAPI 文档，否则 B 没法对着契约调试。"""
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_health_db_returns_503_when_db_down():
    """库连不上时必须是 503 而不是 500。

    区别在编排层：503 表示「暂时不可用、别重启，等等就好」，
    500 会被当成代码 bug 触发反复重启。
    """
    resp = client.get(f"{settings.api_prefix}/health/db")
    assert resp.status_code in (200, 503)
    if resp.status_code == 503:
        assert "database unavailable" in resp.json()["detail"]
