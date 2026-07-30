from collections.abc import AsyncIterator
from pathlib import Path
from time import perf_counter
from urllib.parse import quote

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncResult,
    create_async_engine,
)

from datapulse.datasource.connector import (
    ConnectionTestResult,
    ConnectorSecret,
    NamespaceInfo,
    QueryPolicy,
    RelationField,
    RelationInfo,
    RelationKind,
    RelationSchema,
    StreamColumn,
)
from datapulse.datasource.models import ConnectorType, DatasourceConfig, SQLiteConfig
from datapulse.query.models import ValidatedQuery
from datapulse.query.safety import validate_read_only_sql
from datapulse.settings import Settings


class SQLiteDatasourceInvalid(ValueError):
    pass


def _sqlite_data_type(database_type: object) -> str:
    declared = str(database_type).upper()
    if "INT" in declared:
        return "integer"
    if any(token in declared for token in ("CHAR", "CLOB", "TEXT")):
        return "string"
    if "BLOB" in declared:
        return "binary"
    if any(token in declared for token in ("REAL", "FLOA", "DOUB")):
        return "number"
    if any(token in declared for token in ("NUMERIC", "DECIMAL")):
        return "decimal"
    if "BOOL" in declared:
        return "boolean"
    if "DATETIME" in declared or "TIMESTAMP" in declared:
        return "datetime"
    if "DATE" in declared:
        return "date"
    return "unknown"


class SQLiteQueryStream:
    def __init__(
        self,
        *,
        columns: tuple[StreamColumn, ...],
        result: AsyncResult[tuple[object, ...]],
        connection: AsyncConnection,
        engine: AsyncEngine,
    ) -> None:
        self.columns = columns
        self._result = result
        self._connection = connection
        self._engine = engine
        self._closed = False

    def __aiter__(self) -> AsyncIterator[tuple[object, ...]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[tuple[object, ...]]:
        async for row in self._result:
            yield tuple(row)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._result.close()
        await self._connection.close()
        await self._engine.dispose()


class SQLiteConnector:
    type = ConnectorType.SQLITE
    dialect = "sqlite"

    def __init__(self, settings: Settings) -> None:
        self._sources_dir = settings.resolved_sources_dir()

    def _database_path(self, config: DatasourceConfig) -> Path:
        if not isinstance(config, SQLiteConfig):
            raise SQLiteDatasourceInvalid("SQLite connector requires SQLite config.")
        try:
            root = self._sources_dir.resolve(strict=True)
            database_path = (root / config.path).resolve(strict=True)
        except (FileNotFoundError, OSError) as error:
            raise SQLiteDatasourceInvalid("The SQLite datasource file is invalid.") from error
        if not database_path.is_relative_to(root) or not database_path.is_file():
            raise SQLiteDatasourceInvalid("The SQLite datasource file is invalid.")
        return database_path

    def _engine(self, config: DatasourceConfig) -> AsyncEngine:
        database_path = self._database_path(config)
        encoded_path = quote(database_path.as_posix(), safe="/")
        url = f"sqlite+aiosqlite:///file:{encoded_path}?mode=ro&uri=true"
        return create_async_engine(url)

    async def test_connection(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
    ) -> ConnectionTestResult:
        del secret
        engine = self._engine(config)
        started = perf_counter()
        try:
            async with engine.connect() as connection:
                await connection.exec_driver_sql("PRAGMA query_only=ON")
                await connection.scalar(text("SELECT 1"))
        except Exception:
            return ConnectionTestResult(
                ok=False,
                latency_ms=max(0, round((perf_counter() - started) * 1000)),
                error_code="DATASOURCE_CONNECTION_FAILED",
            )
        finally:
            await engine.dispose()
        return ConnectionTestResult(
            ok=True,
            latency_ms=max(0, round((perf_counter() - started) * 1000)),
        )

    async def list_namespaces(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
    ) -> tuple[NamespaceInfo, ...]:
        del secret
        engine = self._engine(config)
        try:
            async with engine.connect():
                return (NamespaceInfo(name=None),)
        finally:
            await engine.dispose()

    async def list_relations(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
    ) -> tuple[RelationInfo, ...]:
        del secret
        if namespace is not None:
            return ()
        engine = self._engine(config)
        try:
            async with engine.connect() as connection:

                def inspect_relations(sync_connection: object) -> tuple[RelationInfo, ...]:
                    inspector = inspect(sync_connection)
                    tables = tuple(
                        RelationInfo(namespace=None, name=name, kind=RelationKind.TABLE)
                        for name in inspector.get_table_names()
                    )
                    views = tuple(
                        RelationInfo(namespace=None, name=name, kind=RelationKind.VIEW)
                        for name in inspector.get_view_names()
                    )
                    return tuple(sorted(tables + views, key=lambda item: item.name))

                return await connection.run_sync(inspect_relations)
        finally:
            await engine.dispose()

    async def describe_relation(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
        relation: str,
    ) -> RelationSchema:
        del secret
        if namespace is not None:
            raise SQLiteDatasourceInvalid("SQLite does not support namespaces.")
        engine = self._engine(config)
        try:
            async with engine.connect() as connection:

                def inspect_relation(sync_connection: object) -> RelationSchema:
                    inspector = inspect(sync_connection)
                    tables = set(inspector.get_table_names())
                    views = set(inspector.get_view_names())
                    if relation not in tables | views:
                        raise SQLiteDatasourceInvalid("The SQLite relation does not exist.")
                    fields = tuple(
                        RelationField(
                            name=column["name"],
                            data_type=_sqlite_data_type(column["type"]),
                            nullable=bool(column["nullable"]),
                        )
                        for column in inspector.get_columns(relation)
                    )
                    return RelationSchema(
                        namespace=None,
                        name=relation,
                        kind=(RelationKind.TABLE if relation in tables else RelationKind.VIEW),
                        fields=fields,
                    )

                return await connection.run_sync(inspect_relation)
        finally:
            await engine.dispose()

    async def stream_query(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        query: ValidatedQuery,
        parameters: dict[str, object],
        policy: QueryPolicy,
    ) -> SQLiteQueryStream:
        del secret, policy
        validate_read_only_sql(query.sql, self.dialect)
        engine = self._engine(config)
        connection = await engine.connect()
        try:
            await connection.exec_driver_sql("PRAGMA query_only=ON")
            result = await connection.stream(text(query.sql), parameters)
            columns = tuple(StreamColumn(name=name, data_type="unknown") for name in result.keys())
            return SQLiteQueryStream(
                columns=columns,
                result=result,
                connection=connection,
                engine=engine,
            )
        except BaseException:
            await connection.close()
            await engine.dispose()
            raise
