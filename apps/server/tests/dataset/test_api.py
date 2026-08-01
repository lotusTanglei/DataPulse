import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.support.app import AppClient, build_test_app


@pytest.fixture
def dataset_app(tmp_path: Path) -> Iterator[AppClient]:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    with sqlite3.connect(sources_dir / "sales.db") as connection:
        connection.executescript(
            """
            CREATE TABLE sales (
                month TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                region TEXT
            );
            INSERT INTO sales(month, amount, region) VALUES
                ('2026-01', 100, 'north'),
                ('2026-01', 50, 'south'),
                ('2026-02', 200, 'north');
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


def create_source(app_client: AppClient) -> str:
    response = app_client.client.post(
        "/api/admin/datasources",
        json={
            "name": "Sales source",
            "config": {"type": "sqlite", "path": "sales.db"},
        },
        headers=mutation_headers(app_client),
    )
    assert response.status_code == 201
    return response.json()["id"]


def dataset_payload(source_id: str, name: str = "Monthly sales") -> dict[str, object]:
    return {
        "name": name,
        "data_source_id": source_id,
        "sql": ("SELECT month, amount FROM sales WHERE region = :region ORDER BY month"),
        "parameters": [
            {
                "name": "region",
                "data_type": "string",
                "default": "north",
            }
        ],
        "max_rows": 5000,
        "timeout_seconds": 30,
    }


def test_dataset_crud_requires_admin_and_csrf(dataset_app: AppClient) -> None:
    assert dataset_app.client.get("/api/admin/datasets").status_code == 401
    setup_admin(dataset_app)
    source_id = create_source(dataset_app)

    no_csrf = dataset_app.client.post(
        "/api/admin/datasets",
        json=dataset_payload(source_id),
        headers={"Origin": dataset_app.origin},
    )
    assert no_csrf.status_code == 403

    created_response = dataset_app.client.post(
        "/api/admin/datasets",
        json=dataset_payload(source_id),
        headers=mutation_headers(dataset_app),
    )
    assert created_response.status_code == 201
    created = created_response.json()
    dataset_id = created["id"]

    assert created["definition"]["schema_version"] == 1
    assert created["definition"]["query"]["kind"] == "sql"
    assert [field["name"] for field in created["definition"]["fields"]] == [
        "month",
        "amount",
    ]
    assert dataset_app.client.get("/api/admin/datasets").json() == [created]
    assert dataset_app.client.get(f"/api/admin/datasets/{dataset_id}").json() == created

    duplicate = dataset_app.client.post(
        "/api/admin/datasets",
        json=dataset_payload(source_id),
        headers=mutation_headers(dataset_app),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DATASET_NAME_CONFLICT"

    updated = dataset_app.client.patch(
        f"/api/admin/datasets/{dataset_id}",
        json={"name": "Renamed dataset"},
        headers=mutation_headers(dataset_app),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed dataset"

    deleted = dataset_app.client.delete(
        f"/api/admin/datasets/{dataset_id}",
        headers=mutation_headers(dataset_app),
    )
    assert deleted.status_code == 204
    missing = dataset_app.client.get(f"/api/admin/datasets/{dataset_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "DATASET_NOT_FOUND"


def test_dataset_preview_accepts_parameter_values_and_uses_safe_query_path(
    dataset_app: AppClient,
) -> None:
    setup_admin(dataset_app)
    source_id = create_source(dataset_app)
    created = dataset_app.client.post(
        "/api/admin/datasets",
        json=dataset_payload(source_id),
        headers=mutation_headers(dataset_app),
    ).json()

    preview = dataset_app.client.post(
        f"/api/admin/datasets/{created['id']}/preview",
        json={"parameters": {"region": "south"}},
        headers={
            **mutation_headers(dataset_app),
            "X-Request-ID": "dataset-preview-1",
        },
    )

    assert preview.status_code == 200
    assert preview.headers["x-request-id"] == "dataset-preview-1"
    assert preview.json()["request_id"] == "dataset-preview-1"
    assert preview.json()["rows"] == [["2026-01", 50]]

    unsafe = dataset_app.client.post(
        "/api/admin/datasets",
        json={
            **dataset_payload(source_id, name="Unsafe"),
            "sql": "DELETE FROM sales",
        },
        headers=mutation_headers(dataset_app),
    )
    assert unsafe.status_code == 422
    assert unsafe.json()["error"]["code"] == "QUERY_NOT_READ_ONLY"


def test_file_dataset_update_accepts_limits_and_rejects_sql_fields(
    dataset_app: AppClient,
) -> None:
    setup_admin(dataset_app)
    uploaded = dataset_app.client.post(
        "/api/admin/files",
        files={"file": ("sales.csv", b"region,amount\nnorth,10\n", "text/csv")},
        headers=mutation_headers(dataset_app),
    )
    assert uploaded.status_code == 201
    created = dataset_app.client.post(
        "/api/admin/datasets/files",
        json={
            "name": "Sales file",
            "file_asset_id": uploaded.json()["id"],
            "max_rows": 5000,
            "timeout_seconds": 30,
        },
        headers=mutation_headers(dataset_app),
    )
    assert created.status_code == 201
    path = f"/api/admin/datasets/{created.json()['id']}"

    updated = dataset_app.client.patch(
        path,
        json={"name": "Sales renamed", "max_rows": 100, "timeout_seconds": 12},
        headers=mutation_headers(dataset_app),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Sales renamed"
    assert updated.json()["definition"]["max_rows"] == 100
    assert updated.json()["definition"]["timeout_seconds"] == 12

    for invalid_payload in (
        {"sql": "SELECT * FROM dataset_source"},
        {"parameters": []},
    ):
        invalid = dataset_app.client.patch(
            path,
            json=invalid_payload,
            headers=mutation_headers(dataset_app),
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "DATASET_DEFINITION_INVALID"

    deleted = dataset_app.client.delete(
        path,
        headers=mutation_headers(dataset_app),
    )
    assert deleted.status_code == 204
    assert dataset_app.client.get("/api/admin/files").json()[0]["id"] == uploaded.json()["id"]
