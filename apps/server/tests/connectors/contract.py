from dataclasses import dataclass

import pytest

from datapulse.datasource.connector import (
    Connector,
    ConnectorSecret,
    QueryPolicy,
    RelationKind,
)
from datapulse.datasource.models import DatasourceConfig
from datapulse.query.safety import validate_read_only_sql


@dataclass(frozen=True)
class ConnectorCase:
    connector: Connector
    config: DatasourceConfig
    secret: ConnectorSecret | None = None
    namespace: str | None = None
    table_name: str = "sales"
    view_name: str = "monthly_sales"
    table_reference: str = "sales"
    auxiliary_relation: str | None = None


async def collect_stream(stream: object) -> tuple[tuple[object, ...], ...]:
    try:
        return tuple([row async for row in stream])
    finally:
        await stream.aclose()


class ConnectorContract:
    @pytest.fixture
    def connector_case(self) -> ConnectorCase:
        raise NotImplementedError

    @pytest.mark.anyio
    async def test_connection_succeeds(self, connector_case: ConnectorCase) -> None:
        result = await connector_case.connector.test_connection(
            connector_case.config,
            connector_case.secret,
        )

        assert result.ok is True
        assert result.error_code is None
        assert result.latency_ms >= 0

    @pytest.mark.anyio
    async def test_catalog_lists_table_view_and_fields(
        self,
        connector_case: ConnectorCase,
    ) -> None:
        namespaces = await connector_case.connector.list_namespaces(
            connector_case.config,
            connector_case.secret,
        )
        relations = await connector_case.connector.list_relations(
            connector_case.config,
            connector_case.secret,
            connector_case.namespace,
        )
        sales = await connector_case.connector.describe_relation(
            connector_case.config,
            connector_case.secret,
            connector_case.namespace,
            connector_case.table_name,
        )

        assert namespaces
        assert connector_case.namespace in {namespace.name for namespace in namespaces}
        assert {(relation.name, relation.kind) for relation in relations} >= {
            (connector_case.table_name, RelationKind.TABLE),
            (connector_case.view_name, RelationKind.VIEW),
        }
        assert [(field.name, field.data_type, field.nullable) for field in sales.fields] == [
            ("month", "string", False),
            ("amount", "decimal", False),
            ("region", "string", True),
        ]

    @pytest.mark.anyio
    async def test_parameterized_query_duplicate_columns_and_empty_result(
        self,
        connector_case: ConnectorCase,
    ) -> None:
        query = validate_read_only_sql(
            (
                "SELECT month, amount "
                f"FROM {connector_case.table_reference} "
                "WHERE region = :region ORDER BY month"
            ),
            connector_case.connector.dialect,
        )
        stream = await connector_case.connector.stream_query(
            connector_case.config,
            connector_case.secret,
            query,
            {"region": "north"},
            QueryPolicy(),
        )
        columns = tuple(column.name for column in stream.columns)
        rows = await collect_stream(stream)

        assert columns == ("month", "amount")
        assert rows == (("2026-01", 100), ("2026-02", 200))

        duplicate = await connector_case.connector.stream_query(
            connector_case.config,
            connector_case.secret,
            validate_read_only_sql(
                f"SELECT month, month FROM {connector_case.table_reference} LIMIT 1",
                connector_case.connector.dialect,
            ),
            {},
            QueryPolicy(),
        )
        assert tuple(column.name for column in duplicate.columns) == ("month", "month")
        await duplicate.aclose()

        empty = await connector_case.connector.stream_query(
            connector_case.config,
            connector_case.secret,
            validate_read_only_sql(
                f"SELECT month FROM {connector_case.table_reference} WHERE 1 = 0",
                connector_case.connector.dialect,
            ),
            {},
            QueryPolicy(),
        )
        assert tuple(column.name for column in empty.columns) == ("month",)
        assert await collect_stream(empty) == ()
