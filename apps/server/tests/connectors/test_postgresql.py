import os
from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

import pytest
from asyncpg.exceptions import QueryCanceledError, ReadOnlySQLTransactionError
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from datapulse.datasource.connector import ConnectorSecret, QueryPolicy
from datapulse.datasource.models import PostgreSQLConfig
from datapulse.datasource.postgresql import PostgreSQLConnector
from datapulse.query.models import ValidatedQuery
from datapulse.query.safety import validate_read_only_sql
from tests.connectors.contract import ConnectorCase, ConnectorContract, collect_stream

pytestmark = pytest.mark.integration


def _test_url() -> str:
    url = os.getenv("DATAPULSE_TEST_POSTGRES_URL")
    if url is None:
        pytest.skip("DATAPULSE_TEST_POSTGRES_URL is not configured")
    return url


@pytest.fixture
async def postgresql_case() -> AsyncIterator[ConnectorCase]:
    url = make_url(_test_url()).set(drivername="postgresql+asyncpg")
    schema = f"datapulse_{uuid4().hex}"
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.execute(
            text(
                f'CREATE TABLE "{schema}".sales ('
                "month VARCHAR NOT NULL, amount NUMERIC NOT NULL, region VARCHAR)"
            )
        )
        await connection.execute(
            text(
                f'INSERT INTO "{schema}".sales(month, amount, region) VALUES '
                "('2026-01', 100, 'north'), "
                "('2026-01', 50, 'south'), "
                "('2026-02', 200, 'north')"
            )
        )
        await connection.execute(
            text(
                f'CREATE VIEW "{schema}".monthly_sales AS '
                f'SELECT month, SUM(amount) AS amount FROM "{schema}".sales GROUP BY month'
            )
        )
        await connection.execute(
            text(
                f'CREATE TABLE "{schema}".postgres_types ('
                "happened_at TIMESTAMPTZ, amount NUMERIC, event_id UUID, "
                "payload JSONB, tags TEXT[])"
            )
        )
    parsed = url
    case = ConnectorCase(
        connector=PostgreSQLConnector(),
        config=PostgreSQLConfig(
            host=parsed.host or "",
            port=parsed.port or 5432,
            database=parsed.database or "",
            username=parsed.username or "",
            ssl_mode="disable",
        ),
        secret=ConnectorSecret(password=parsed.password or ""),
        namespace=schema,
        table_reference=f'"{schema}".sales',
    )
    try:
        yield case
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await engine.dispose()


class TestPostgreSQLConnector(ConnectorContract):
    @pytest.fixture
    def connector_case(self, postgresql_case: ConnectorCase) -> ConnectorCase:
        return postgresql_case


@pytest.mark.anyio
async def test_postgresql_catalog_maps_native_types(
    postgresql_case: ConnectorCase,
) -> None:
    schema = await postgresql_case.connector.describe_relation(
        postgresql_case.config,
        postgresql_case.secret,
        postgresql_case.namespace,
        "postgres_types",
    )

    assert [(field.name, field.data_type) for field in schema.fields] == [
        ("happened_at", "datetime"),
        ("amount", "decimal"),
        ("event_id", "uuid"),
        ("payload", "json"),
        ("tags", "array"),
    ]


@pytest.mark.anyio
async def test_postgresql_applies_statement_timeout(
    postgresql_case: ConnectorCase,
) -> None:
    started = perf_counter()
    with pytest.raises(QueryCanceledError):
        stream = await postgresql_case.connector.stream_query(
            postgresql_case.config,
            postgresql_case.secret,
            validate_read_only_sql("SELECT pg_sleep(2)", "postgres"),
            {},
            QueryPolicy(timeout_seconds=1),
        )
        await collect_stream(stream)

    assert perf_counter() - started < 1.8


@pytest.mark.anyio
async def test_postgresql_database_rejects_write_when_validator_is_bypassed(
    postgresql_case: ConnectorCase,
) -> None:
    bypassed = ValidatedQuery(
        sql=(
            f"INSERT INTO {postgresql_case.table_reference}(month, amount) VALUES ('2026-03', 300)"
        ),
        dialect="postgres",
        query_hash="0" * 64,
    )

    with pytest.raises(ReadOnlySQLTransactionError):
        stream = await postgresql_case.connector.stream_query(
            postgresql_case.config,
            postgresql_case.secret,
            bypassed,
            {},
            QueryPolicy(),
        )
        await collect_stream(stream)

    check = await postgresql_case.connector.stream_query(
        postgresql_case.config,
        postgresql_case.secret,
        validate_read_only_sql(
            f"SELECT COUNT(*) FROM {postgresql_case.table_reference}",
            "postgres",
        ),
        {},
        QueryPolicy(),
    )
    assert await collect_stream(check) == ((3,),)
