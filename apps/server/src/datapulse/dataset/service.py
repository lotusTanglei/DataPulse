from collections.abc import Callable
from uuid import uuid4

from datapulse.contracts.dataset import (
    DatasetDefinition,
    DatasetField,
    DataType,
    SqlQuery,
)
from datapulse.dataset.models import (
    DatasetCreate,
    DatasetPreviewRequest,
    DatasetResponse,
    DatasetUpdate,
)
from datapulse.dataset.repository import DatasetRepository
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.service import DatasourceService
from datapulse.query.models import QueryColumn, QueryRequest, QueryResult
from datapulse.query.safety import validate_read_only_sql


def _field_type(column: QueryColumn) -> DataType:
    try:
        return DataType(column.data_type)
    except ValueError:
        if column.data_type in {"decimal", "float"}:
            return DataType.NUMBER
        return DataType.STRING


def _fields(result: QueryResult) -> tuple[DatasetField, ...]:
    return tuple(
        DatasetField(name=column.name, data_type=_field_type(column)) for column in result.columns
    )


class DatasetService:
    def __init__(
        self,
        *,
        repository: DatasetRepository,
        datasource_service: DatasourceService,
        registry: ConnectorRegistry,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._datasource_service = datasource_service
        self._registry = registry
        self._id_factory = id_factory or (lambda: str(uuid4()))

    async def list(self) -> tuple[DatasetResponse, ...]:
        return await self._repository.list()

    async def get(self, dataset_id: str) -> DatasetResponse:
        return await self._repository.get(dataset_id)

    async def create(
        self,
        data: DatasetCreate,
        *,
        request_id: str,
    ) -> DatasetResponse:
        source = await self._datasource_service.get(data.data_source_id)
        connector = self._registry.get(source.config.type)
        validate_read_only_sql(data.sql, connector.dialect)
        parameter_values = {parameter.name: parameter.default for parameter in data.parameters}
        result = await self._datasource_service.query(
            data.data_source_id,
            QueryRequest(
                sql=data.sql,
                parameters=parameter_values,
                max_rows=data.max_rows,
                timeout_seconds=data.timeout_seconds,
            ),
            request_id=request_id,
            trigger="dataset-save",
        )
        definition = DatasetDefinition(
            id=self._id_factory(),
            name=data.name,
            data_source_id=data.data_source_id,
            query=SqlQuery(sql=data.sql),
            fields=_fields(result),
            parameters=data.parameters,
            max_rows=data.max_rows,
            timeout_seconds=data.timeout_seconds,
        )
        return await self._repository.create(definition)

    async def update(
        self,
        dataset_id: str,
        data: DatasetUpdate,
        *,
        request_id: str,
    ) -> DatasetResponse:
        existing = await self._repository.get(dataset_id)
        definition = existing.definition
        if not isinstance(definition.query, SqlQuery):
            raise ValueError("Only SQL datasets can be edited.")
        sql = data.sql or definition.query.sql
        parameters = data.parameters if data.parameters is not None else definition.parameters
        max_rows = data.max_rows or definition.max_rows
        timeout_seconds = data.timeout_seconds or definition.timeout_seconds
        fields = definition.fields
        if data.sql is not None or data.parameters is not None:
            source = await self._datasource_service.get(existing.data_source_id)
            connector = self._registry.get(source.config.type)
            validate_read_only_sql(sql, connector.dialect)
            result = await self._datasource_service.query(
                existing.data_source_id,
                QueryRequest(
                    sql=sql,
                    parameters={parameter.name: parameter.default for parameter in parameters},
                    max_rows=max_rows,
                    timeout_seconds=timeout_seconds,
                ),
                request_id=request_id,
                dataset_id=dataset_id,
                trigger="dataset-update",
            )
            fields = _fields(result)
        updated = definition.model_copy(
            update={
                "name": data.name or definition.name,
                "query": SqlQuery(sql=sql),
                "parameters": parameters,
                "fields": fields,
                "max_rows": max_rows,
                "timeout_seconds": timeout_seconds,
            }
        )
        return await self._repository.update(dataset_id, updated)

    async def delete(self, dataset_id: str) -> None:
        await self._repository.delete(dataset_id)

    async def preview(
        self,
        dataset_id: str,
        data: DatasetPreviewRequest,
        *,
        request_id: str,
    ) -> QueryResult:
        dataset = await self._repository.get(dataset_id)
        definition = dataset.definition
        if not isinstance(definition.query, SqlQuery):
            raise ValueError("Only SQL datasets can be previewed.")
        source = await self._datasource_service.get(dataset.data_source_id)
        connector = self._registry.get(source.config.type)
        validate_read_only_sql(definition.query.sql, connector.dialect)
        return await self._datasource_service.query(
            dataset.data_source_id,
            QueryRequest(
                sql=definition.query.sql,
                parameters=data.parameters,
                max_rows=definition.max_rows,
                timeout_seconds=definition.timeout_seconds,
            ),
            request_id=request_id,
            dataset_id=dataset_id,
            trigger="dataset-preview",
        )
