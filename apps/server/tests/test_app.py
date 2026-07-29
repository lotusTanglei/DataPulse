from fastapi.testclient import TestClient

from datapulse.app import create_app
from datapulse.settings import Settings


def test_health_returns_status_and_version() -> None:
    app = create_app(Settings(app_version="0.1.0", environment="test"))
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
