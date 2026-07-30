import os
from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from datapulse.datasource.connector import ConnectorSecret, QueryPolicy
from datapulse.datasource.models import MySQLConfig
from datapulse.datasource.mysql import MySQLConnector
from datapulse.query.models import ValidatedQuery
from datapulse.query.safety import validate_read_only_sql
from tests.connectors.contract import ConnectorCase, ConnectorContract, collect_stream

pytestmark = pytest.mark.integration


def _test_url() -> str:
    url = os.getenv("DATAPULSE_TEST_MYSQL_URL")
    if url is None:
        pytest.skip("DATAPULSE_TEST_MYSQL_URL is not configured")
    return url


@pytest.fixture
async def mysql_case() -> AsyncIterator[ConnectorCase]:
    url = make_url(_test_url()).set(drivername="mysql+asyncmy")
    suffix = uuid4().hex
    table_name = f"sales_{suffix}"
    view_name = f"monthly_sales_{suffix}"
    types_name = f"mysql_types_{suffix}"
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                f"""
                CREATE TABLE `{table_name}` (
                    month VARCHAR(20) NOT NULL,
                    amount DECIMAL(20, 2) NOT NULL,
                    region VARCHAR(50)
                );
                INSERT INTO `{table_name}`(month, amount, region) VALUES
                    ('2026-01', 100, 'north'),
                    ('2026-01', 50, 'south'),
                    ('2026-02', 200, 'north');
                CREATE VIEW `{view_name}` AS
                    SELECT month, SUM(amount) AS amount
                    FROM `{table_name}` GROUP BY month;
                CREATE TABLE `{types_name}` (
                    signed_value INT,
                    unsigned_value INT UNSIGNED,
                    amount DECIMAL(20, 4),
                    happened_at DATETIME,
                    payload JSON,
                    content BLOB
                );
                """
            )
        )
    parsed = url
    case = ConnectorCase(
        connector=MySQLConnector(),
        config=MySQLConfig(
            host=parsed.host or "",
            port=parsed.port or 3306,
            database=parsed.database or "",
            username=parsed.username or "",
            ssl_mode="disabled",
        ),
        secret=ConnectorSecret(password=parsed.password or ""),
        namespace=parsed.database,
        table_name=table_name,
        view_name=view_name,
        table_reference=f"`{table_name}`",
        auxiliary_relation=types_name,
    )
    try:
        yield case
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f"DROP VIEW IF EXISTS `{view_name}`"))
            await connection.execute(text(f"DROP TABLE IF EXISTS `{table_name}`, `{types_name}`"))
        await engine.dispose()


class TestMySQLConnector(ConnectorContract):
    @pytest.fixture
    def connector_case(self, mysql_case: ConnectorCase) -> ConnectorCase:
        return mysql_case


@pytest.mark.anyio
async def test_mysql_catalog_maps_native_types(mysql_case: ConnectorCase) -> None:
    schema = await mysql_case.connector.describe_relation(
        mysql_case.config,
        mysql_case.secret,
        mysql_case.namespace,
        mysql_case.auxiliary_relation or "",
    )

    assert [(field.name, field.data_type) for field in schema.fields] == [
        ("signed_value", "integer"),
        ("unsigned_value", "integer"),
        ("amount", "decimal"),
        ("happened_at", "datetime"),
        ("payload", "json"),
        ("content", "binary"),
    ]


@pytest.mark.anyio
async def test_mysql_applies_driver_timeout(mysql_case: ConnectorCase) -> None:
    started = perf_counter()
    with pytest.raises(OperationalError):
        stream = await mysql_case.connector.stream_query(
            mysql_case.config,
            mysql_case.secret,
            validate_read_only_sql("SELECT SLEEP(2)", "mysql"),
            {},
            QueryPolicy(timeout_seconds=1),
        )
        await collect_stream(stream)

    assert perf_counter() - started < 1.8


@pytest.mark.anyio
async def test_mysql_database_rejects_write_when_validator_is_bypassed(
    mysql_case: ConnectorCase,
) -> None:
    bypassed = ValidatedQuery(
        sql=(f"INSERT INTO {mysql_case.table_reference}(month, amount) VALUES ('2026-03', 300)"),
        dialect="mysql",
        query_hash="0" * 64,
    )

    with pytest.raises(OperationalError):
        stream = await mysql_case.connector.stream_query(
            mysql_case.config,
            mysql_case.secret,
            bypassed,
            {},
            QueryPolicy(),
        )
        await collect_stream(stream)

    check = await mysql_case.connector.stream_query(
        mysql_case.config,
        mysql_case.secret,
        validate_read_only_sql(
            f"SELECT COUNT(*) FROM {mysql_case.table_reference}",
            "mysql",
        ),
        {},
        QueryPolicy(),
    )
    assert await collect_stream(check) == ((3,),)
