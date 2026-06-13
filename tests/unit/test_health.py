"""Basic smoke test for the /health endpoint."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


def _mock_db():
    db = MagicMock()
    db.execute.return_value = None
    return db


def test_health_returns_ok():
    with patch("api.routers.health.get_db", return_value=iter([_mock_db()])):
        client = TestClient(app)
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "timestamp" in body
    assert "services" in body
