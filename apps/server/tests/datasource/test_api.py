import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from datapulse.query.execution import QueryExecutionError
from tests.support.app import AppClient, build_test_app


@pytest.fixture
def datasource_app(tmp_path: Path) -> Iterator[AppClient]:
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
            CREATE VIEW monthly_sales AS
            SELECT month, SUM(amount) AS amount FROM sales GROUP BY month;
            INSERT INTO sales(month, amount, region) VALUES
                ('2026-01', 100, 'north'),
                ('2026-01', 50, 'south'),
                ('2026-02', 200, 'north');
            """
        )
    with build_test_app(tmp_path) as app_client:
        yield app_client


def mutation_headers(app_client: AppClient) -> dict[str, str]:
    return {
        "Origin": app_client.origin,
        "X-CSRF-Token": app_client.client.cookies["datapulse_csrf"],
    }


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


def create_source(app_client: AppClient, name: str = "Sales") -> dict[str, object]:
    response = app_client.client.post(
        "/api/admin/datasources",
        json={
            "name": name,
            "config": {"type": "sqlite", "path": "sales.db"},
        },
        headers=mutation_headers(app_client),
    )
    assert response.status_code == 201
    return response.json()


def test_datasource_crud_requires_admin_and_csrf(
    datasource_app: AppClient,
) -> None:
    assert datasource_app.client.get("/api/admin/datasources").status_code == 401
    setup_admin(datasource_app)

    missing_csrf = datasource_app.client.post(
        "/api/admin/datasources",
        json={
            "name": "Sales",
            "config": {"type": "sqlite", "path": "sales.db"},
        },
        headers={"Origin": datasource_app.origin},
    )
    assert missing_csrf.status_code == 403

    missing_key = datasource_app.client.post(
        "/api/admin/datasources",
        json={
            "name": "Protected",
            "config": {"type": "sqlite", "path": "sales.db"},
            "password": "must-never-leak",
        },
        headers=mutation_headers(datasource_app),
    )
    assert missing_key.status_code == 503
    assert missing_key.json()["error"]["code"] == "DATASOURCE_SECRET_KEY_MISSING"
    assert "must-never-leak" not in missing_key.text

    created = create_source(datasource_app)
    datasource_id = created["id"]

    assert created["name"] == "Sales"
    assert created["has_password"] is False
    assert "password" not in created
    assert "secret_envelope" not in created
    assert datasource_app.client.get("/api/admin/datasources").json() == [created]
    assert datasource_app.client.get(f"/api/admin/datasources/{datasource_id}").json() == created

    duplicate = datasource_app.client.post(
        "/api/admin/datasources",
        json={
            "name": "Sales",
            "config": {"type": "sqlite", "path": "sales.db"},
        },
        headers=mutation_headers(datasource_app),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DATASOURCE_NAME_CONFLICT"

    updated = datasource_app.client.patch(
        f"/api/admin/datasources/{datasource_id}",
        json={"name": "Renamed"},
        headers=mutation_headers(datasource_app),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"

    tested = datasource_app.client.post(
        f"/api/admin/datasources/{datasource_id}/test",
        headers=mutation_headers(datasource_app),
    )
    assert tested.status_code == 200
    assert tested.json()["status"] == "available"

    deleted = datasource_app.client.delete(
        f"/api/admin/datasources/{datasource_id}",
        headers=mutation_headers(datasource_app),
    )
    assert deleted.status_code == 204
    missing = datasource_app.client.get(f"/api/admin/datasources/{datasource_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "DATASOURCE_NOT_FOUND"


def test_catalog_and_parameterized_query_use_real_sqlite(
    datasource_app: AppClient,
) -> None:
    setup_admin(datasource_app)
    datasource_id = create_source(datasource_app)["id"]

    namespaces = datasource_app.client.get(f"/api/admin/datasources/{datasource_id}/namespaces")
    relations = datasource_app.client.get(
        f"/api/admin/datasources/{datasource_id}/relations",
        params={"namespace": ""},
    )
    relation = datasource_app.client.get(
        f"/api/admin/datasources/{datasource_id}/relation",
        params={"namespace": "", "relation": "sales"},
    )

    assert namespaces.status_code == 200
    assert namespaces.json() == [{"name": None}]
    assert {(item["name"], item["kind"]) for item in relations.json()} >= {
        ("sales", "table"),
        ("monthly_sales", "view"),
    }
    assert [field["name"] for field in relation.json()["fields"]] == [
        "month",
        "amount",
        "region",
    ]

    query = datasource_app.client.post(
        f"/api/admin/datasources/{datasource_id}/query",
        json={
            "sql": ("SELECT month, amount FROM sales WHERE region = :region ORDER BY month"),
            "parameters": {"region": "north"},
            "max_rows": 1000,
            "timeout_seconds": 30,
        },
        headers={
            **mutation_headers(datasource_app),
            "X-Request-ID": "debug-query-1",
        },
    )

    assert query.status_code == 200
    assert query.headers["x-request-id"] == "debug-query-1"
    assert query.json()["request_id"] == "debug-query-1"
    assert query.json()["columns"] == [
        {"name": "month", "data_type": "unknown"},
        {"name": "amount", "data_type": "unknown"},
    ]
    assert query.json()["rows"] == [["2026-01", 100], ["2026-02", 200]]

    rejected = datasource_app.client.post(
        f"/api/admin/datasources/{datasource_id}/query",
        json={"sql": "DELETE FROM sales"},
        headers=mutation_headers(datasource_app),
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "QUERY_NOT_READ_ONLY"


@pytest.mark.parametrize(
    ("code", "status_code"),
    [
        ("QUERY_TIMEOUT", 504),
        ("QUERY_CONCURRENCY_LIMITED", 429),
    ],
)
def test_query_execution_errors_keep_stable_status(
    datasource_app: AppClient,
    code: str,
    status_code: int,
) -> None:
    setup_admin(datasource_app)
    datasource_id = create_source(datasource_app)["id"]

    class FailingExecutor:
        async def execute(self, **kwargs: object) -> None:
            raise QueryExecutionError(
                code,
                status_code,
                str(kwargs["request_id"]),
            )

    datasource_app.client.app.state.datasource_service._query_executor = FailingExecutor()
    response = datasource_app.client.post(
        f"/api/admin/datasources/{datasource_id}/query",
        json={"sql": "SELECT month FROM sales"},
        headers={
            **mutation_headers(datasource_app),
            "X-Request-ID": f"{code.lower()}-request",
        },
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
