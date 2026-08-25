import base64
import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from datapulse.embedding.page import TicketRedactionFilter
from tests.support.app import AppClient, build_test_app

SIGNING_KEY = base64.urlsafe_b64encode(b"e" * 32).decode()
HOST_ORIGIN = "https://host.example.com"


@pytest.fixture
def embed_app(tmp_path: Path) -> Iterator[AppClient]:
    static_dir = tmp_path / "web"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        "<!doctype html><title>DataPulse player</title>",
        encoding="utf-8",
    )
    with build_test_app(
        tmp_path,
        signing_key=SIGNING_KEY,
        static_dir=static_dir,
    ) as app_client:
        yield app_client


@pytest.fixture
def runtime_embed_app(tmp_path: Path) -> Iterator[AppClient]:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    with sqlite3.connect(sources_dir / "sales.db") as connection:
        connection.executescript(
            """
            CREATE TABLE sales (month TEXT NOT NULL, amount NUMERIC NOT NULL);
            INSERT INTO sales(month, amount) VALUES ('2026-01', 100), ('2026-02', 200);
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


def create_parameterized_screen(app_client: AppClient, name: str = "Embedded") -> str:
    created = app_client.client.post(
        "/api/admin/screens",
        json={"name": name},
        headers=mutation_headers(app_client),
    ).json()
    document = {
        "canvas": {"width": 1920, "height": 1080},
        "parameters": [
            {
                "id": "region",
                "name": "region",
                "data_type": "string",
                "default": "east",
                "mutable": True,
                "allowed_values": ["east", "west"],
            },
            {
                "id": "year",
                "name": "year",
                "data_type": "integer",
                "default": 2026,
                "mutable": False,
            },
        ],
    }
    saved = app_client.client.patch(
        f"/api/admin/screens/{created['id']}",
        json={"draft_document": document, "expected_revision": 0},
        headers=mutation_headers(app_client),
    )
    assert saved.status_code == 200
    published = app_client.client.post(
        f"/api/admin/screens/{created['id']}/publish",
        json={"expected_revision": 1},
        headers=mutation_headers(app_client),
    )
    assert published.status_code == 200
    return str(created["id"])


def rotate_api_key(app_client: AppClient) -> str:
    response = app_client.client.post(
        "/api/admin/embed/api-key",
        headers=mutation_headers(app_client),
    )
    assert response.status_code == 201
    return str(response.json()["api_key"])


def issue_ticket(
    app_client: AppClient,
    *,
    api_key: str,
    screen_id: str,
    origin: str = HOST_ORIGIN,
    parameters: dict[str, object] | None = None,
    mutable_parameters: list[str] | None = None,
) -> str:
    response = app_client.client.post(
        "/api/embed/tickets",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "screen_id": screen_id,
            "allowed_origin": origin,
            "parameters": ({"region": "west"} if parameters is None else parameters),
            "mutable_parameters": (
                ["region"] if mutable_parameters is None else mutable_parameters
            ),
            "lifetime_seconds": 3600,
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["ticket"])


def test_ticket_endpoint_requires_host_api_key_and_rotation_invalidates_old_key(
    embed_app: AppClient,
) -> None:
    setup_admin(embed_app)
    screen_id = create_parameterized_screen(embed_app)
    first_key = rotate_api_key(embed_app)

    session_only = embed_app.client.post(
        "/api/embed/tickets",
        json={
            "screen_id": screen_id,
            "allowed_origin": HOST_ORIGIN,
            "lifetime_seconds": 3600,
        },
    )
    assert session_only.status_code == 401

    ticket = issue_ticket(embed_app, api_key=first_key, screen_id=screen_id)
    loaded = embed_app.client.get(
        f"/api/embed/screens/{screen_id}",
        headers={"Authorization": f"Bearer {ticket}"},
    )
    assert loaded.status_code == 200
    assert loaded.json()["document"]["parameters"][0]["name"] == "region"
    assert loaded.json()["parameters"] == {"region": "west", "year": 2026}
    assert loaded.json()["mutable_parameters"] == ["region"]
    assert loaded.headers["cache-control"] == "no-store"
    assert loaded.headers["referrer-policy"] == "no-referrer"
    assert loaded.headers["content-security-policy"] == (f"frame-ancestors {HOST_ORIGIN}")

    rotate_api_key(embed_app)
    denied = embed_app.client.post(
        "/api/embed/tickets",
        headers={"Authorization": f"Bearer {first_key}"},
        json={
            "screen_id": screen_id,
            "allowed_origin": HOST_ORIGIN,
            "lifetime_seconds": 3600,
        },
    )
    assert denied.status_code == 401


def test_runtime_rejects_wrong_screen_and_immutable_parameter(
    embed_app: AppClient,
) -> None:
    setup_admin(embed_app)
    screen_id = create_parameterized_screen(embed_app)
    other_id = create_parameterized_screen(embed_app, "Other")
    ticket = issue_ticket(
        embed_app,
        api_key=rotate_api_key(embed_app),
        screen_id=screen_id,
    )

    assert embed_app.client.get(f"/api/embed/screens/{screen_id}").status_code == 401
    wrong_screen = embed_app.client.get(
        f"/api/embed/screens/{other_id}",
        headers={"Authorization": f"Bearer {ticket}"},
    )
    assert wrong_screen.status_code == 401
    immutable = embed_app.client.post(
        f"/api/embed/screens/{screen_id}/query",
        headers={"Authorization": f"Bearer {ticket}"},
        json={"component_id": "missing", "parameters": {"year": 2027}},
    )
    assert immutable.status_code == 403
    assert immutable.json()["error"]["code"] == "EMBED_PARAMETER_DENIED"


def test_embed_runtime_queries_and_assets_are_scoped_to_published_document(
    runtime_embed_app: AppClient,
) -> None:
    setup_admin(runtime_embed_app)
    source = runtime_embed_app.client.post(
        "/api/admin/datasources",
        headers=mutation_headers(runtime_embed_app),
        json={
            "name": "Sales source",
            "config": {"type": "sqlite", "path": "sales.db"},
        },
    ).json()
    dataset = runtime_embed_app.client.post(
        "/api/admin/datasets",
        headers=mutation_headers(runtime_embed_app),
        json={
            "name": "Monthly sales",
            "data_source_id": source["id"],
            "sql": "SELECT month, amount FROM sales",
        },
    ).json()
    referenced_asset = runtime_embed_app.client.post(
        "/api/admin/assets",
        headers=mutation_headers(runtime_embed_app),
        files={"file": ("logo.png", b"\x89PNG\r\n\x1a\nsafe", "image/png")},
    ).json()
    unrelated_asset = runtime_embed_app.client.post(
        "/api/admin/assets",
        headers=mutation_headers(runtime_embed_app),
        files={"file": ("other.png", b"\x89PNG\r\n\x1a\nother", "image/png")},
    ).json()
    created = runtime_embed_app.client.post(
        "/api/admin/screens",
        headers=mutation_headers(runtime_embed_app),
        json={"name": "Runtime embed"},
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
                        "dataset_id": dataset["id"],
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
                "props": {"asset_id": referenced_asset["id"]},
            },
        ],
    }
    saved = runtime_embed_app.client.patch(
        f"/api/admin/screens/{created['id']}",
        headers=mutation_headers(runtime_embed_app),
        json={"draft_document": document, "expected_revision": 0},
    )
    assert saved.status_code == 200
    published = runtime_embed_app.client.post(
        f"/api/admin/screens/{created['id']}/publish",
        headers=mutation_headers(runtime_embed_app),
        json={"expected_revision": 1},
    )
    assert published.status_code == 200
    ticket = issue_ticket(
        runtime_embed_app,
        api_key=rotate_api_key(runtime_embed_app),
        screen_id=str(created["id"]),
        parameters={},
        mutable_parameters=[],
    )
    bearer = {"Authorization": f"Bearer {ticket}"}

    query = runtime_embed_app.client.post(
        f"/api/embed/screens/{created['id']}/query",
        headers=bearer,
        json={"component_id": "line-1"},
    )
    assert query.status_code == 200
    assert query.json()["rows"] == [["2026-01", 100], ["2026-02", 200]]
    referenced = runtime_embed_app.client.get(
        f"/api/embed/screens/{created['id']}/assets/{referenced_asset['id']}",
        headers=bearer,
    )
    assert referenced.status_code == 200
    assert referenced.content.startswith(b"\x89PNG")
    unrelated = runtime_embed_app.client.get(
        f"/api/embed/screens/{created['id']}/assets/{unrelated_asset['id']}",
        headers=bearer,
    )
    assert unrelated.status_code == 404
    assert unrelated.json()["error"]["code"] == "ASSET_NOT_FOUND"


def test_embed_page_verifies_ticket_origin_and_sets_exact_csp(
    embed_app: AppClient,
) -> None:
    setup_admin(embed_app)
    screen_id = create_parameterized_screen(embed_app)
    ticket = issue_ticket(
        embed_app,
        api_key=rotate_api_key(embed_app),
        screen_id=screen_id,
    )

    allowed = embed_app.client.get(
        f"/embed/{screen_id}",
        params={"ticket": ticket},
        headers={"Origin": HOST_ORIGIN},
    )
    assert allowed.status_code == 200
    assert "DataPulse player" in allowed.text
    assert allowed.headers["content-security-policy"] == (f"frame-ancestors {HOST_ORIGIN}")
    assert allowed.headers["cache-control"] == "no-store"
    assert allowed.headers["referrer-policy"] == "no-referrer"

    denied = embed_app.client.get(
        f"/embed/{screen_id}",
        params={"ticket": ticket},
        headers={"Origin": "https://evil.example.com"},
    )
    assert denied.status_code == 403
    assert "DataPulse player" not in denied.text


def test_access_log_filter_redacts_ticket_query_parameter() -> None:
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=(
            "127.0.0.1",
            "GET",
            "/embed/screen-1?ticket=super-secret&mode=fit",
            "1.1",
            200,
        ),
        exc_info=None,
    )

    assert TicketRedactionFilter().filter(record)
    assert "super-secret" not in record.getMessage()
    assert "ticket=%5BREDACTED%5D" in record.getMessage()
