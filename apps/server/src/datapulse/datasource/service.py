import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import RestQuery
from datapulse.datasource.connector import (
    Connector,
    ConnectorSecret,
    NamespaceInfo,
    QueryPolicy,
    RelationInfo,
    RelationSchema,
)
from datapulse.datasource.engine_manager import EngineManager
from datapulse.datasource.http_api import HttpApiConnector
from datapulse.datasource.models import (
    DatasourceCreate,
    DatasourceResponse,
    DatasourceStatus,
    DatasourceUpdate,
)
from datapulse.datasource.registry import ConnectorNotFound, ConnectorRegistry
from datapulse.datasource.repository import DatasourceRepository
from datapulse.datasource.secrets import SecretBox, SecretEnvelope
from datapulse.errors import DataPulseError
from datapulse.query.execution import QueryExecutor
from datapulse.query.models import QueryRequest, QueryResult

logger = logging.getLogger(__name__)


def translate_connector_error(error: Exception, request_id: str) -> DataPulseError:
    logger.warning(
        "Datasource operation failed",
        extra={
            "error_code": "DATASOURCE_OPERATION_FAILED",
            "request_id": request_id,
            "exception_type": type(error).__name__,
        },
    )
    return DataPulseError(
        code="DATASOURCE_OPERATION_FAILED",
        message="The datasource operation failed.",
        status_code=502,
    )


class DatasourceService:
    def __init__(
        self,
        *,
        repository: DatasourceRepository,
        secret_box: SecretBox | None,
        registry: ConnectorRegistry,
        engine_manager: EngineManager,
        query_executor: QueryExecutor | None,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._secret_box = secret_box
        self._registry = registry
        self._engine_manager = engine_manager
        self._query_executor = query_executor
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(UTC))

    def _connector(self, datasource: DatasourceResponse) -> Connector:
        try:
            return self._registry.get(datasource.config.type)
        except ConnectorNotFound as error:
            raise DataPulseError(
                code="DATASOURCE_CONNECTOR_UNAVAILABLE",
                message="The datasource connector is unavailable.",
                status_code=422,
            ) from error

    def _encrypt(self, datasource_id: str, password: str) -> SecretEnvelope:
        if self._secret_box is None:
            raise DataPulseError(
                code="DATASOURCE_SECRET_KEY_MISSING",
                message="A datasource master key is required to store passwords.",
                status_code=503,
            )
        return self._secret_box.encrypt(datasource_id, password)

    async def _secret(self, datasource_id: str) -> ConnectorSecret | None:
        envelope = await self._repository.get_secret_envelope(datasource_id)
        if envelope is None:
            return None
        if self._secret_box is None:
            raise DataPulseError(
                code="DATASOURCE_SECRET_KEY_MISSING",
                message="A datasource master key is required to read passwords.",
                status_code=503,
            )
        return ConnectorSecret(password=self._secret_box.decrypt(datasource_id, envelope))

    async def create(self, data: DatasourceCreate) -> DatasourceResponse:
        try:
            self._registry.get(data.config.type)
        except ConnectorNotFound as error:
            raise DataPulseError(
                code="DATASOURCE_CONNECTOR_UNAVAILABLE",
                message="The datasource connector is unavailable.",
                status_code=422,
            ) from error
        datasource_id = self._id_factory()
        envelope = (
            None
            if data.password is None
            else self._encrypt(datasource_id, data.password.get_secret_value())
        )
        return await self._repository.create(
            datasource_id,
            data,
            secret_envelope=envelope,
        )

    async def list(self) -> tuple[DatasourceResponse, ...]:
        return await self._repository.list()

    async def get(self, datasource_id: str) -> DatasourceResponse:
        return await self._repository.get(datasource_id)

    async def dialect(self, datasource_id: str) -> str:
        datasource = await self._repository.get(datasource_id)
        return self._connector(datasource).dialect

    async def update(
        self,
        datasource_id: str,
        data: DatasourceUpdate,
    ) -> DatasourceResponse:
        existing = await self._repository.get(datasource_id)
        if data.config is not None:
            try:
                self._registry.get(data.config.type)
            except ConnectorNotFound as error:
                raise DataPulseError(
                    code="DATASOURCE_CONNECTOR_UNAVAILABLE",
                    message="The datasource connector is unavailable.",
                    status_code=422,
                ) from error
        envelope = (
            None
            if data.password is None
            else self._encrypt(datasource_id, data.password.get_secret_value())
        )
        if data.password is None:
            updated = await self._repository.update(datasource_id, data)
        else:
            updated = await self._repository.update(
                datasource_id,
                data,
                secret_envelope=envelope,
            )
        connection_changed = (
            (data.config is not None and data.config != existing.config)
            or data.password is not None
            or data.clear_password
        )
        if connection_changed:
            await self._engine_manager.dispose(datasource_id)
        return updated

    async def delete(self, datasource_id: str) -> None:
        await self._repository.delete(datasource_id)
        await self._engine_manager.dispose(datasource_id)

    async def test_connection(self, datasource_id: str) -> DatasourceResponse:
        datasource = await self._repository.get(datasource_id)
        connector = self._connector(datasource)
        secret = await self._secret(datasource_id)
        try:
            result = await connector.test_connection(datasource.config, secret)
        except Exception:
            result_status = DatasourceStatus.UNAVAILABLE
            latency_ms = 0
            error_code = "DATASOURCE_CONNECTION_FAILED"
        else:
            result_status = (
                DatasourceStatus.AVAILABLE if result.ok else DatasourceStatus.UNAVAILABLE
            )
            latency_ms = result.latency_ms
            error_code = None if result.ok else result.error_code or "DATASOURCE_CONNECTION_FAILED"
        return await self._repository.update_connection_status(
            datasource_id,
            status=result_status,
            checked_at=self._clock(),
            latency_ms=latency_ms,
            error_code=error_code,
        )

    async def _connection_context(
        self,
        datasource_id: str,
    ) -> tuple[DatasourceResponse, Connector, ConnectorSecret | None]:
        datasource = await self._repository.get(datasource_id)
        return datasource, self._connector(datasource), await self._secret(datasource_id)

    async def list_namespaces(
        self,
        datasource_id: str,
        *,
        request_id: str,
    ) -> tuple[NamespaceInfo, ...]:
        datasource, connector, secret = await self._connection_context(datasource_id)
        try:
            return await connector.list_namespaces(datasource.config, secret)
        except Exception as error:
            raise translate_connector_error(error, request_id) from error

    async def list_relations(
        self,
        datasource_id: str,
        namespace: str | None,
        *,
        request_id: str,
    ) -> tuple[RelationInfo, ...]:
        datasource, connector, secret = await self._connection_context(datasource_id)
        try:
            return await connector.list_relations(datasource.config, secret, namespace)
        except Exception as error:
            raise translate_connector_error(error, request_id) from error

    async def describe_relation(
        self,
        datasource_id: str,
        namespace: str | None,
        relation: str,
        *,
        request_id: str,
    ) -> RelationSchema:
        datasource, connector, secret = await self._connection_context(datasource_id)
        try:
            return await connector.describe_relation(
                datasource.config,
                secret,
                namespace,
                relation,
            )
        except Exception as error:
            raise translate_connector_error(error, request_id) from error

    async def preview_relation(
        self,
        datasource_id: str,
        namespace: str | None,
        relation: str,
        *,
        limit: int,
        request_id: str,
    ) -> QueryResult:
        """Return a bounded preview for a discovered relation."""
        if limit < 1 or limit > 100:
            raise DataPulseError(
                code="DATASOURCE_PREVIEW_LIMIT_INVALID",
                message="The preview limit must be between 1 and 100.",
                status_code=422,
            )
        _, connector, _ = await self._connection_context(datasource_id)
        schema = await self.describe_relation(
            datasource_id,
            namespace,
            relation,
            request_id=request_id,
        )
        quote = "`" if connector.dialect == "mysql" else '"'

        def quoted(identifier: str) -> str:
            return f"{quote}{identifier.replace(quote, quote + quote)}{quote}"

        qualified = quoted(schema.name)
        if schema.namespace:
            qualified = f"{quoted(schema.namespace)}.{qualified}"
        return await self.query(
            datasource_id,
            QueryRequest(
                sql=f"SELECT * FROM {qualified} LIMIT {limit}",
                max_rows=limit,
                timeout_seconds=30,
            ),
            request_id=request_id,
            trigger="relation-preview",
        )

    async def query(
        self,
        datasource_id: str,
        query_request: QueryRequest,
        *,
        request_id: str,
        dataset_id: str | None = None,
        trigger: str = "debug",
    ) -> QueryResult:
        if self._query_executor is None:
            raise RuntimeError("The query executor is unavailable.")
        datasource, connector, secret = await self._connection_context(datasource_id)
        return await self._query_executor.execute(
            datasource_id=datasource_id,
            dataset_id=dataset_id,
            trigger=trigger,
            connector=connector,
            config=datasource.config,
            secret=secret,
            request=query_request,
            request_id=request_id,
        )

    async def rest_query(
        self,
        datasource_id: str,
        query: RestQuery,
        *,
        parameters: dict[str, JsonValue],
        max_rows: int,
        timeout_seconds: int,
        request_id: str,
    ) -> QueryResult:
        datasource, connector, secret = await self._connection_context(datasource_id)
        if not isinstance(connector, HttpApiConnector):
            raise DataPulseError(
                code="DATASET_QUERY_SOURCE_INVALID",
                message="REST queries require an HTTP API datasource.",
                status_code=422,
            )
        try:
            return await connector.execute_rest(
                datasource.config,
                secret,
                query,
                parameters=parameters,
                policy=QueryPolicy(max_rows=max_rows, timeout_seconds=timeout_seconds),
                request_id=request_id,
            )
        except Exception as error:
            raise translate_connector_error(error, request_id) from error
