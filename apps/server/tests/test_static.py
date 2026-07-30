from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.static import create_spa_router
from tests.support.app import build_test_app


def test_spa_serves_assets_and_falls_back_to_index(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<h1>DataPulse</h1>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("export {}", encoding="utf-8")
    app = FastAPI()
    app.include_router(create_spa_router(tmp_path))
    client = TestClient(app)

    assert client.get("/assets/app.js").text == "export {}"
    assert "DataPulse" in client.get("/screens/demo").text


def test_spa_does_not_swallow_api_404(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>DataPulse</h1>", encoding="utf-8")
    app = FastAPI()
    app.include_router(create_spa_router(tmp_path))

    assert TestClient(app).get("/api/missing").status_code == 404


def test_spa_returns_clear_404_when_web_is_not_built(tmp_path: Path) -> None:
    app = FastAPI()
    app.include_router(create_spa_router(tmp_path))

    response = TestClient(app).get("/screens/demo")

    assert response.status_code == 404
    assert response.json() == {"detail": "Web application is not built"}


def test_spa_does_not_serve_files_outside_static_directory(tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>DataPulse</h1>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("not public", encoding="utf-8")
    app = FastAPI()
    app.include_router(create_spa_router(static_dir))

    response = TestClient(app).get("/%2e%2e/secret.txt")

    assert response.status_code == 200
    assert "DataPulse" in response.text
    assert "not public" not in response.text


def test_app_mounts_configured_static_directory(tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        "<h1>Configured DataPulse</h1>",
        encoding="utf-8",
    )

    with build_test_app(tmp_path, static_dir=static_dir) as app_client:
        response = app_client.client.get("/")
        health = app_client.client.get("/api/health")

    assert response.status_code == 200
    assert "Configured DataPulse" in response.text
    assert health.json() == {"status": "ok", "version": "0.1.0"}
