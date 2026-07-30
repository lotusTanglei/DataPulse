from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from pydantic import Field, SecretStr

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.datasource.models import ConnectorType, DatasourceConfig

if TYPE_CHECKING:
    from datapulse.query.models import ValidatedQuery


class ConnectorSecret(ContractModel):
    password: SecretStr


class ConnectionTestResult(ContractModel):
    ok: bool
    latency_ms: int = Field(ge=0)
    error_code: str | None = None


class NamespaceInfo(ContractModel):
    name: str | None


class RelationKind(StrEnum):
    TABLE = "table"
    VIEW = "view"


class RelationInfo(ContractModel):
    namespace: str | None
    name: NonBlankStr
    kind: RelationKind


class RelationField(ContractModel):
    name: NonBlankStr
    data_type: NonBlankStr
    nullable: bool


class RelationSchema(ContractModel):
    namespace: str | None
    name: NonBlankStr
    kind: RelationKind
    fields: tuple[RelationField, ...]


class QueryPolicy(ContractModel):
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_rows: int = Field(default=1000, ge=1, le=5000)


class StreamColumn(ContractModel):
    name: str
    data_type: NonBlankStr


class QueryStream(Protocol):
    columns: tuple[StreamColumn, ...]

    def __aiter__(self) -> AsyncIterator[tuple[object, ...]]: ...

    async def aclose(self) -> None: ...


class Connector(Protocol):
    type: ConnectorType
    dialect: str

    async def test_connection(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
    ) -> ConnectionTestResult: ...

    async def list_namespaces(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
    ) -> tuple[NamespaceInfo, ...]: ...

    async def list_relations(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
    ) -> tuple[RelationInfo, ...]: ...

    async def describe_relation(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        namespace: str | None,
        relation: str,
    ) -> RelationSchema: ...

    async def stream_query(
        self,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        query: ValidatedQuery,
        parameters: dict[str, JsonValue],
        policy: QueryPolicy,
    ) -> QueryStream: ...
