from pathlib import Path

from tests.support.app import build_test_app


def test_health_returns_status_and_version(tmp_path: Path) -> None:
    with build_test_app(tmp_path, app_version="0.1.0") as app_client:
        response = app_client.client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
