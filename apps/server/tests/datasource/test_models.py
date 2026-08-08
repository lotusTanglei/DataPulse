from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from datapulse.datasource.models import (
    ConnectorType,
    DatasourceCreate,
    DatasourceResponse,
    DatasourceStatus,
    DatasourceUpdate,
    HttpApiConfig,
    MySQLConfig,
    PostgreSQLConfig,
    SQLiteConfig,
)


def test_postgresql_create_parses_discriminated_config() -> None:
    created = DatasourceCreate.model_validate(
        {
            "name": "Sales",
            "config": {
                "type": "postgresql",
                "host": "db.internal",
                "port": 5432,
                "database": "sales",
                "username": "reader",
                "ssl_mode": "prefer",
            },
            "password": "secret",
        }
    )

    assert isinstance(created.config, PostgreSQLConfig)
    assert created.config.type is ConnectorType.POSTGRESQL
    assert created.password is not None
    assert created.password.get_secret_value() == "secret"


def test_connector_defaults_are_explicit() -> None:
    postgresql = PostgreSQLConfig(
        host="db.internal",
        database="sales",
        username="reader",
    )
    mysql = MySQLConfig(
        host="db.internal",
        database="sales",
        username="reader",
    )

    assert postgresql.port == 5432
    assert postgresql.ssl_mode == "prefer"
    assert mysql.port == 3306
    assert mysql.ssl_mode == "preferred"


def test_http_api_auth_requires_secret_on_create() -> None:
    with pytest.raises(ValidationError):
        DatasourceCreate(
            name="Remote",
            config=HttpApiConfig(
                base_url="https://api.example.com",
                auth_type="bearer",
            ),
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "sqlite", "path": "/tmp/sales.db"},
        {"type": "sqlite", "path": "../sales.db"},
        {"type": "sqlite", "path": "demo/../../sales.db"},
        {"type": "sqlite", "path": ""},
    ],
)
def test_sqlite_config_rejects_paths_outside_source_root(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        SQLiteConfig.model_validate(payload)


@pytest.mark.parametrize("port", [0, 65536])
def test_remote_config_rejects_invalid_ports(port: int) -> None:
    with pytest.raises(ValidationError):
        PostgreSQLConfig(
            host="db.internal",
            port=port,
            database="sales",
            username="reader",
        )


def test_models_reject_unknown_fields_and_blank_names() -> None:
    with pytest.raises(ValidationError):
        DatasourceCreate.model_validate(
            {
                "name": " ",
                "config": {"type": "sqlite", "path": "sales.db"},
                "unexpected": True,
            }
        )


def test_update_rejects_password_and_clear_password_together() -> None:
    with pytest.raises(ValidationError):
        DatasourceUpdate(password="replacement", clear_password=True)


def test_response_never_serializes_secret_material() -> None:
    now = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
    response = DatasourceResponse(
        id="source-id",
        name="Sales",
        config=SQLiteConfig(path="sales.db"),
        status=DatasourceStatus.UNKNOWN,
        has_password=True,
        created_at=now,
        updated_at=now,
    )

    payload = response.model_dump(mode="json")

    assert payload["has_password"] is True
    assert "password" not in payload
    assert "ciphertext" not in payload
    assert "nonce" not in payload
    assert "url" not in payload
