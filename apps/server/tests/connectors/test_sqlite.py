import sqlite3
from pathlib import Path

import pytest

from datapulse.datasource.connector import QueryPolicy
from datapulse.datasource.models import SQLiteConfig
from datapulse.datasource.sqlite import SQLiteConnector, SQLiteDatasourceInvalid
from datapulse.query.models import ValidatedQuery
from datapulse.query.safety import QueryValidationError
from datapulse.settings import Settings
from tests.connectors.contract import ConnectorCase, ConnectorContract, collect_stream


@pytest.fixture
def sqlite_case(tmp_path: Path) -> ConnectorCase:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    database_path = sources_dir / "sales.db"
    with sqlite3.connect(database_path) as connection:
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
    connector = SQLiteConnector(
        Settings(
            environment="test",
            data_dir=tmp_path,
            sources_dir=sources_dir,
        )
    )
    return ConnectorCase(
        connector=connector,
        config=SQLiteConfig(path="sales.db"),
    )


class TestSQLiteConnector(ConnectorContract):
    @pytest.fixture
    def connector_case(self, sqlite_case: ConnectorCase) -> ConnectorCase:
        return sqlite_case


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/tmp/sales.db",
        "../sales.db",
        "missing.db",
        "directory",
        "escape.db",
    ],
)
async def test_sqlite_rejects_unsafe_or_invalid_paths(
    sqlite_case: ConnectorCase,
    tmp_path: Path,
    path: str,
) -> None:
    sources_dir = tmp_path / "sources"
    (sources_dir / "directory").mkdir()
    outside = tmp_path / "outside.db"
    outside.touch()
    symlink = sources_dir / "escape.db"
    symlink.symlink_to(outside)
    unsafe_config = SQLiteConfig.model_construct(type="sqlite", path=path)

    with pytest.raises(SQLiteDatasourceInvalid):
        await sqlite_case.connector.test_connection(unsafe_config, None)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO sales(month, amount) VALUES ('2026-03', 1)",
        "ATTACH DATABASE '/tmp/secret.db' AS secret",
        "PRAGMA writable_schema = 1",
        "SELECT load_extension('/tmp/extension')",
    ],
)
async def test_sqlite_defense_rejects_commands_when_safety_layer_is_bypassed(
    sqlite_case: ConnectorCase,
    tmp_path: Path,
    sql: str,
) -> None:
    bypassed = ValidatedQuery(
        sql=sql,
        dialect="sqlite",
        query_hash="0" * 64,
    )

    with pytest.raises(QueryValidationError):
        stream = await sqlite_case.connector.stream_query(
            sqlite_case.config,
            None,
            bypassed,
            {},
            QueryPolicy(),
        )
        await collect_stream(stream)

    with sqlite3.connect(tmp_path / "sources" / "sales.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone() == (3,)
