import re
from time import perf_counter

from sqlalchemy import URL, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from datapulse.datasource._sqlalchemy import SQLAlchemyQueryStream
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
from datapulse.datasource.models import ConnectorType, DatasourceConfig, MySQLConfig
from datapulse.query.models import ValidatedQuery


class MySQLDatasourceInvalid(ValueError):
    pass


_json_column_pattern = re.compile(r"json_valid\(`([^`]+)`\)", re.IGNORECASE)


def _mysql_data_type(database_type: object, *, json_alias: bool = False) -> str:
    declared = str(database_type).upper()
    class_name = type(database_type).__name__.upper()
    if json_alias or "JSON" in class_name or "JSON" in declared:
        return "json"
    if "DATETIME" in class_name or "TIMESTAMP" in class_name:
        return "datetime"
    if class_name == "DATE":
        return "date"
    if "DECIMAL" in class_name or "NUMERIC" in class_name:
        return "decimal"
    if "FLOAT" in class_name or "DOUBLE" in class_name or "REAL" in class_name:
        return "number"
    if "INT" in class_name:
        return "integer"
    if "BOOL" in class_name or "BOOLEAN" in class_name:
        return "boolean"
    if "BLOB" in class_name or "BINARY" in class_name:
        return "binary"
    if any(token in class_name for token in ("CHAR", "TEXT", "STRING")):
        return "string"
    return "unknown"


class MySQLConnector:
    type = ConnectorType.MYSQL
    dialect = "mysql"

    def _engine(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        *,
        read_timeout: int = 30,
    ) -> AsyncEngine:
        if not isinstance(config, MySQLConfig):
            raise MySQLDatasourceInvalid("MySQL connector requires MySQL config.")
        password = None if secret is None else secret.password.get_secret_value()
        url = URL.create(
            "mysql+asyncmy",
            username=config.username,
            password=password,
            host=config.host,
            port=config.port,
            database=config.database,
        )
        connect_args: dict[str, object] = {"read_timeout": read_timeout}
        if config.ssl_mode == "required":
            connect_args["ssl"] = {}
        return create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
            connect_args=connect_args,
        )

    async def test_connection(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
    ) -> ConnectionTestResult:
        engine = self._engine(config, secret)
        started = perf_counter()
        try:
            async with engine.connect() as connection:
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
        engine = self._engine(config, secret)
        try:
            async with engine.connect() as connection:

                def inspect_namespaces(sync_connection: object) -> tuple[NamespaceInfo, ...]:
                    names = inspect(sync_connection).get_schema_names()
                    hidden = {"information_schema", "mysql", "performance_schema", "sys"}
                    return tuple(
                        NamespaceInfo(name=name) for name in sorted(names) if name not in hidden
                    )

                return await connection.run_sync(inspect_namespaces)
        finally:
            await engine.dispose()

    async def list_relations(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
    ) -> tuple[RelationInfo, ...]:
        engine = self._engine(config, secret)
        try:
            async with engine.connect() as connection:

                def inspect_relations(sync_connection: object) -> tuple[RelationInfo, ...]:
                    inspector = inspect(sync_connection)
                    tables = tuple(
                        RelationInfo(namespace=namespace, name=name, kind=RelationKind.TABLE)
                        for name in inspector.get_table_names(schema=namespace)
                    )
                    views = tuple(
                        RelationInfo(namespace=namespace, name=name, kind=RelationKind.VIEW)
                        for name in inspector.get_view_names(schema=namespace)
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
        engine = self._engine(config, secret)
        try:
            async with engine.connect() as connection:
                schema_name = namespace
                if schema_name is None and isinstance(config, MySQLConfig):
                    schema_name = config.database
                constraint_rows = await connection.execute(
                    text(
                        "SELECT CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS "
                        "WHERE CONSTRAINT_SCHEMA = :namespace AND TABLE_NAME = :relation"
                    ),
                    {"namespace": schema_name, "relation": relation},
                )
                json_columns = {
                    match.group(1)
                    for row in constraint_rows
                    if (match := _json_column_pattern.search(str(row[0])))
                }

                def inspect_relation(sync_connection: object) -> RelationSchema:
                    inspector = inspect(sync_connection)
                    tables = set(inspector.get_table_names(schema=namespace))
                    views = set(inspector.get_view_names(schema=namespace))
                    if relation not in tables | views:
                        raise MySQLDatasourceInvalid("The MySQL relation does not exist.")
                    fields = tuple(
                        RelationField(
                            name=column["name"],
                            data_type=_mysql_data_type(
                                column["type"],
                                json_alias=column["name"] in json_columns,
                            ),
                            nullable=bool(column["nullable"]),
                        )
                        for column in inspector.get_columns(relation, schema=namespace)
                    )
                    return RelationSchema(
                        namespace=namespace,
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
    ) -> SQLAlchemyQueryStream:
        engine = self._engine(config, secret, read_timeout=policy.timeout_seconds)
        connection = await engine.connect()
        transaction = None
        try:
            await connection.exec_driver_sql("START TRANSACTION READ ONLY")
            transaction = connection.get_transaction()
            if transaction is None:
                raise RuntimeError("MariaDB did not start a transaction.")
            result = await connection.stream(text(query.sql), parameters)
            columns = tuple(StreamColumn(name=name, data_type="unknown") for name in result.keys())
            return SQLAlchemyQueryStream(
                columns=columns,
                result=result,
                transaction=transaction,
                connection=connection,
                engine=engine,
            )
        except BaseException:
            if transaction is not None and transaction.is_active:
                await transaction.rollback()
            await connection.close()
            await engine.dispose()
            raise
