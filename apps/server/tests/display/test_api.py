import base64
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.support.app import AppClient, build_test_app
from tests.support.media import image_bytes

SIGNING_KEY = base64.urlsafe_b64encode(b"s" * 32).decode()


@pytest.fixture
def display_app(tmp_path: Path) -> Iterator[AppClient]:
    with build_test_app(tmp_path, signing_key=SIGNING_KEY) as app_client:
        yield app_client


@pytest.fixture
def runtime_display_app(tmp_path: Path) -> Iterator[AppClient]:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    with sqlite3.connect(sources_dir / "sales.db") as connection:
        connection.executescript(
            """
            CREATE TABLE sales (
                month TEXT NOT NULL,
                amount NUMERIC NOT NULL
            );
            INSERT INTO sales(month, amount) VALUES
                ('2026-01', 100),
                ('2026-02', 200);
            """
        )
    with build_test_app(tmp_path, signing_key=SIGNING_KEY) as app_client:
        yield app_client


def setup_admin(app_client: AppClient) -> None:
    response = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": app_client.origin},
    )
    assert response.status_code == 201


def mutation_headers(app_client: AppClient) -> dict[str, str]:
    return {
        "Origin": app_client.origin,
        "X-CSRF-Token": app_client.client.cookies["datapulse_csrf"],
    }


def create_and_publish_screen(app_client: AppClient) -> dict[str, object]:
    created = app_client.client.post(
        "/api/admin/screens",
        json={"name": "Operations"},
        headers=mutation_headers(app_client),
    ).json()
    published = app_client.client.post(
        f"/api/admin/screens/{created['id']}/publish",
        json={"expected_revision": 0},
        headers=mutation_headers(app_client),
    )
    assert published.status_code == 200
    return published.json()


def create_dataset(app_client: AppClient) -> str:
    source = app_client.client.post(
        "/api/admin/datasources",
        json={
            "name": "Sales source",
            "config": {"type": "sqlite", "path": "sales.db"},
        },
        headers=mutation_headers(app_client),
    )
    assert source.status_code == 201
    dataset = app_client.client.post(
        "/api/admin/datasets",
        json={
            "name": "Monthly sales",
            "data_source_id": source.json()["id"],
            "sql": "SELECT month, amount FROM sales",
        },
        headers=mutation_headers(app_client),
    )
    assert dataset.status_code == 201
    return dataset.json()["id"]


def authorize_display(app_client: AppClient, screen_id: str) -> None:
    generated = app_client.client.post(
        f"/api/admin/screens/{screen_id}/display-key",
        headers=mutation_headers(app_client),
    )
    assert generated.status_code == 201
    exchanged = app_client.client.post(
        f"/api/player/screens/{screen_id}/session",
        json={"key": generated.json()["key"]},
    )
    assert exchanged.status_code == 204


def test_display_key_exchange_document_and_rotation(
    display_app: AppClient,
) -> None:
    setup_admin(display_app)
    screen = create_and_publish_screen(display_app)
    screen_id = str(screen["id"])

    generated = display_app.client.post(
        f"/api/admin/screens/{screen_id}/display-key",
        headers=mutation_headers(display_app),
    )
    assert generated.status_code == 201
    assert generated.json()["key_version"] == 1
    plaintext = generated.json()["key"]

    before_exchange = display_app.client.get(f"/api/player/screens/{screen_id}")
    assert before_exchange.status_code == 401

    exchanged = display_app.client.post(
        f"/api/player/screens/{screen_id}/session",
        json={"key": plaintext},
    )
    assert exchanged.status_code == 204
    cookie = exchanged.headers["set-cookie"]
    assert "datapulse_display=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/player" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie

    loaded = display_app.client.get(f"/api/player/screens/{screen_id}")
    assert loaded.status_code == 200
    assert loaded.json()["document"] == screen["published_document"]
    assert "datapulse_display=" in loaded.headers["set-cookie"]

    rotated = display_app.client.post(
        f"/api/admin/screens/{screen_id}/display-key",
        headers=mutation_headers(display_app),
    )
    assert rotated.status_code == 201
    assert rotated.json()["key_version"] == 2
    assert display_app.client.get(f"/api/player/screens/{screen_id}").status_code == 401


def test_display_exchange_rejects_invalid_key_and_unpublished_screen(
    display_app: AppClient,
) -> None:
    setup_admin(display_app)
    published = create_and_publish_screen(display_app)
    published_id = str(published["id"])
    display_app.client.post(
        f"/api/admin/screens/{published_id}/display-key",
        headers=mutation_headers(display_app),
    )
    invalid = display_app.client.post(
        f"/api/player/screens/{published_id}/session",
        json={"key": "invalid"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "DISPLAY_ACCESS_DENIED"

    draft = display_app.client.post(
        "/api/admin/screens",
        json={"name": "Draft"},
        headers=mutation_headers(display_app),
    ).json()
    key = display_app.client.post(
        f"/api/admin/screens/{draft['id']}/display-key",
        headers=mutation_headers(display_app),
    ).json()["key"]
    unavailable = display_app.client.post(
        f"/api/player/screens/{draft['id']}/session",
        json={"key": key},
    )
    assert unavailable.status_code == 409
    assert unavailable.json()["error"]["code"] == "DISPLAY_SCREEN_UNAVAILABLE"


def test_display_runtime_scopes_queries_and_assets_to_published_screen(
    runtime_display_app: AppClient,
) -> None:
    setup_admin(runtime_display_app)
    dataset_id = create_dataset(runtime_display_app)
    referenced_asset = runtime_display_app.client.post(
        "/api/admin/assets",
        files={"file": ("logo.png", image_bytes(), "image/png")},
        headers=mutation_headers(runtime_display_app),
    )
    unrelated_asset = runtime_display_app.client.post(
        "/api/admin/assets",
        files={"file": ("other.png", image_bytes(color="#ff0000"), "image/png")},
        headers=mutation_headers(runtime_display_app),
    )
    assert referenced_asset.status_code == 201
    assert unrelated_asset.status_code == 201
    created = runtime_display_app.client.post(
        "/api/admin/screens",
        json={"name": "Runtime"},
        headers=mutation_headers(runtime_display_app),
    ).json()
    document = {
        "canvas": {"width": 1920, "height": 1080},
        "components": [
            {
                "id": "line-1",
                "type": "builtin.line",
                "frame": {"x": 0, "y": 0, "width": 640, "height": 320},
                "data_binding": {
                    "chart_spec": {
                        "dataset_id": dataset_id,
                        "dimensions": ["month"],
                        "measures": [{"field": "amount", "aggregation": "sum"}],
                        "visual": {"type": "line"},
                    }
                },
            },
            {
                "id": "image-1",
                "type": "builtin.image",
                "frame": {"x": 0, "y": 340, "width": 320, "height": 180},
                "props": {"asset_id": referenced_asset.json()["id"]},
            },
        ],
    }
    saved = runtime_display_app.client.patch(
        f"/api/admin/screens/{created['id']}",
        json={"draft_document": document, "expected_revision": 0},
        headers=mutation_headers(runtime_display_app),
    )
    assert saved.status_code == 200
    published = runtime_display_app.client.post(
        f"/api/admin/screens/{created['id']}/publish",
        json={"expected_revision": 1},
        headers=mutation_headers(runtime_display_app),
    )
    assert published.status_code == 200
    authorize_display(runtime_display_app, created["id"])

    query = runtime_display_app.client.post(
        f"/api/player/screens/{created['id']}/query",
        json={"component_id": "line-1", "parameters": {}},
        headers={"X-Request-ID": "display-query"},
    )
    assert query.status_code == 200
    assert query.json()["rows"] == [["2026-01", 100], ["2026-02", 200]]

    referenced = runtime_display_app.client.get(
        f"/api/player/screens/{created['id']}/assets/{referenced_asset.json()['id']}"
    )
    assert referenced.status_code == 200
    assert referenced.content.startswith(b"\x89PNG")

    unrelated = runtime_display_app.client.get(
        f"/api/player/screens/{created['id']}/assets/{unrelated_asset.json()['id']}"
    )
    assert unrelated.status_code == 404
    assert unrelated.json()["error"]["code"] == "ASSET_NOT_FOUND"

    with sqlite3.connect(runtime_display_app.database_path) as connection:
        connection.execute(
            "UPDATE screen_asset SET storage_path = ? WHERE id = ?",
            ("/private/outside-asset-root/secret.png", referenced_asset.json()["id"]),
        )
    invalid = runtime_display_app.client.get(
        f"/api/player/screens/{created['id']}/assets/{referenced_asset.json()['id']}"
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "ASSET_INVALID"
    assert "secret.png" not in invalid.text
