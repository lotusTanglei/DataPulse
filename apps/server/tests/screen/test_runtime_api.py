import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.support.app import AppClient, build_test_app


@pytest.fixture
def runtime_app(tmp_path: Path) -> Iterator[AppClient]:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    with sqlite3.connect(sources_dir / "sales.db") as connection:
        connection.executescript(
            """
            CREATE TABLE sales (
                month TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                region TEXT NOT NULL
            );
            INSERT INTO sales(month, amount, region) VALUES
                ('2026-01', 100, 'east'),
                ('2026-01', 50, 'west'),
                ('2026-02', 200, 'east');
            """
        )
    with build_test_app(tmp_path) as app_client:
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
            "sql": "SELECT month, amount, region FROM sales",
        },
        headers=mutation_headers(app_client),
    )
    assert dataset.status_code == 201
    return dataset.json()["id"]


def create_bound_screen(app_client: AppClient, dataset_id: str) -> str:
    created = app_client.client.post(
        "/api/admin/screens",
        json={"name": "Operations"},
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
                "allowed_values": ["east", "west"],
            }
        ],
        "components": [
            {
                "id": "line-1",
                "type": "builtin.line",
                "frame": {"x": 40, "y": 40, "width": 640, "height": 320},
                "data_binding": {
                    "chart_spec": {
                        "dataset_id": dataset_id,
                        "dimensions": ["month"],
                        "measures": [{"field": "amount", "aggregation": "sum"}],
                        "filters": [
                            {
                                "field": "region",
                                "operator": "equals",
                                "value": {"kind": "parameter", "name": "region"},
                            }
                        ],
                        "visual": {"type": "line"},
                    }
                },
            }
        ],
    }
    saved = app_client.client.patch(
        f"/api/admin/screens/{created['id']}",
        json={"draft_document": document, "expected_revision": 0},
        headers=mutation_headers(app_client),
    )
    assert saved.status_code == 200
    return created["id"]


def test_admin_runtime_query_executes_only_stored_binding(
    runtime_app: AppClient,
) -> None:
    setup_admin(runtime_app)
    dataset_id = create_dataset(runtime_app)
    screen_id = create_bound_screen(runtime_app, dataset_id)

    response = runtime_app.client.post(
        f"/api/admin/screens/{screen_id}/query",
        json={"component_id": "line-1", "parameters": {"region": "west"}},
        headers={**mutation_headers(runtime_app), "X-Request-ID": "screen-query-1"},
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "screen-query-1"
    assert response.json()["rows"] == [["2026-01", 50]]

    arbitrary_query = runtime_app.client.post(
        f"/api/admin/screens/{screen_id}/query",
        json={
            "component_id": "line-1",
            "dataset_id": "attacker-selected",
            "sql": "SELECT 1",
        },
        headers=mutation_headers(runtime_app),
    )
    assert arbitrary_query.status_code == 422
    assert arbitrary_query.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_admin_runtime_query_requires_csrf_and_maps_component_errors(
    runtime_app: AppClient,
) -> None:
    setup_admin(runtime_app)
    dataset_id = create_dataset(runtime_app)
    screen_id = create_bound_screen(runtime_app, dataset_id)

    no_csrf = runtime_app.client.post(
        f"/api/admin/screens/{screen_id}/query",
        json={"component_id": "line-1"},
        headers={"Origin": runtime_app.origin},
    )
    assert no_csrf.status_code == 403

    missing = runtime_app.client.post(
        f"/api/admin/screens/{screen_id}/query",
        json={"component_id": "missing"},
        headers=mutation_headers(runtime_app),
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "SCREEN_COMPONENT_UNAVAILABLE"
