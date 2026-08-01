from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from datapulse.contracts.dataset import (
    DatasetDefinition,
    DatasetField,
    DataType,
    FileQuery,
    SqlQuery,
)
from datapulse.contracts.filedata import FileDatasetCreate
from datapulse.dataset.models import (
    DatasetCreate,
    DatasetPreviewRequest,
    DatasetResponse,
    DatasetUpdate,
)
from datapulse.dataset.repository import DatasetRepository
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.service import DatasourceService
from datapulse.filedata.parsers import parse_file
from datapulse.filedata.query import FileDatasetQueryService
from datapulse.filedata.repository import FileAssetRepository
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
        file_asset_repository: FileAssetRepository | None = None,
        file_query_service: FileDatasetQueryService | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._datasource_service = datasource_service
        self._registry = registry
        self._file_asset_repository = file_asset_repository
        self._file_query_service = file_query_service
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

    async def create_file(
        self,
        data: FileDatasetCreate,
        *,
        request_id: str,
    ) -> DatasetResponse:
        del request_id
        if self._file_asset_repository is None:
            raise RuntimeError("file asset repository is not configured")
        asset = await self._file_asset_repository.get(data.file_asset_id)
        parsed = await parse_file(
            Path(asset.storage_path),
            asset.format,
            sheet_name=data.sheet_name,
            max_rows=data.max_rows,
        )
        definition = DatasetDefinition(
            id=self._id_factory(),
            name=data.name,
            data_source_id=None,
            query=FileQuery(
                asset_id=asset.id,
                format=asset.format,
                sheet_name=data.sheet_name,
            ),
            fields=parsed.fields,
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
        if isinstance(definition.query, SqlQuery):
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
        if isinstance(definition.query, FileQuery):
            if self._file_asset_repository is None or self._file_query_service is None:
                raise RuntimeError("file dataset services are not configured")
            asset = await self._file_asset_repository.get(definition.query.asset_id)
            parsed = await parse_file(
                Path(asset.storage_path),
                definition.query.format,
                sheet_name=definition.query.sheet_name,
                max_rows=definition.max_rows,
            )
            return await self._file_query_service.preview(
                request_id=request_id,
                source_path=parsed.normalized_path,
                max_rows=definition.max_rows,
                timeout_seconds=definition.timeout_seconds,
            )
        raise ValueError("Unsupported dataset query type.")
