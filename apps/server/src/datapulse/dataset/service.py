from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from datapulse.contracts.dataset import (
    DatasetDefinition,
    DatasetField,
    DatasetFieldOverride,
    DataType,
    FileQuery,
    RestQuery,
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
from datapulse.filedata.inference import infer_type, merge_types
from datapulse.filedata.parsers import parse_file
from datapulse.filedata.query import FileDatasetQueryService
from datapulse.filedata.repository import FileAssetRepository
from datapulse.query.models import QueryColumn, QueryRequest, QueryResult
from datapulse.query.safety import validate_read_only_sql


class DatasetUpdateInvalid(ValueError):
    code = "DATASET_DEFINITION_INVALID"


def _field_type(column: QueryColumn) -> DataType:
    try:
        return DataType(column.data_type)
    except ValueError:
        if column.data_type in {"decimal", "float"}:
            return DataType.NUMBER
        return DataType.STRING


def _fields(result: QueryResult) -> tuple[DatasetField, ...]:
    fields: list[DatasetField] = []
    for index, column in enumerate(result.columns):
        data_type = _field_type(column)
        if column.data_type.casefold() == "unknown":
            inferred: DataType | None = None
            for row in result.rows:
                if index >= len(row) or row[index] is None:
                    continue
                inferred = merge_types(inferred, infer_type(row[index]))
            data_type = inferred or data_type
        fields.append(DatasetField(name=column.name, data_type=data_type))
    return tuple(fields)


def _apply_field_overrides(
    fields: tuple[DatasetField, ...],
    overrides: tuple[DatasetFieldOverride, ...],
) -> tuple[DatasetField, ...]:
    by_name = {item.name: item for item in overrides}
    return tuple(
        field.model_copy(update={"data_type": by_name[field.name].data_type})
        if field.name in by_name and by_name[field.name].data_type is not None
        else field
        for field in fields
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
        parameter_values = {parameter.name: parameter.default for parameter in data.parameters}
        if data.query is not None:
            result = await self._datasource_service.rest_query(
                data.data_source_id,
                query=data.query,
                parameters=parameter_values,
                max_rows=data.max_rows,
                timeout_seconds=data.timeout_seconds,
                request_id=request_id,
            )
            definition_query = data.query
        else:
            # DatasetCreate validates that exactly one query form is present.
            assert data.sql is not None
            validate_read_only_sql(data.sql, connector.dialect)
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
            definition_query = SqlQuery(sql=data.sql)
        definition = DatasetDefinition(
            id=self._id_factory(),
            name=data.name,
            data_source_id=data.data_source_id,
            query=definition_query,
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
        overrides = (
            data.profile_overrides
            if data.profile_overrides is not None
            else definition.profile_overrides
        )
        if data.profile_overrides is not None:
            known = {field.name for field in definition.fields}
            if any(item.name not in known for item in data.profile_overrides):
                raise DatasetUpdateInvalid("Profile overrides reference unknown fields.")
        if isinstance(definition.query, FileQuery):
            if data.sql is not None or data.parameters is not None:
                raise DatasetUpdateInvalid("SQL and parameters are not valid for file datasets.")
            if self._file_asset_repository is None:
                raise RuntimeError("file asset repository is not configured")
            max_rows = data.max_rows or definition.max_rows
            timeout_seconds = data.timeout_seconds or definition.timeout_seconds
            asset = await self._file_asset_repository.get(definition.query.asset_id)
            parsed = await parse_file(
                Path(asset.storage_path),
                definition.query.format,
                sheet_name=definition.query.sheet_name,
                max_rows=max_rows,
            )
            updated = definition.model_copy(
                update={
                    "name": data.name or definition.name,
                    "fields": _apply_field_overrides(parsed.fields, overrides),
                    "profile_overrides": overrides,
                    "max_rows": max_rows,
                    "timeout_seconds": timeout_seconds,
                }
            )
            return await self._repository.update(dataset_id, updated)
        if isinstance(definition.query, RestQuery):
            if data.sql is not None:
                raise DatasetUpdateInvalid("SQL is not valid for REST datasets.")
            query = data.query or definition.query
            if data.query is not None:
                result = await self._datasource_service.rest_query(
                    existing.data_source_id,
                    query=query,
                    parameters={
                        parameter.name: parameter.default for parameter in definition.parameters
                    },
                    max_rows=data.max_rows or definition.max_rows,
                    timeout_seconds=data.timeout_seconds or definition.timeout_seconds,
                    request_id=request_id,
                )
                fields = _fields(result)
            else:
                fields = definition.fields
            fields = _apply_field_overrides(fields, overrides)
            updated = definition.model_copy(
                update={
                    "name": data.name or definition.name,
                    "query": query,
                    "fields": fields,
                    "profile_overrides": overrides,
                    "max_rows": data.max_rows or definition.max_rows,
                    "timeout_seconds": data.timeout_seconds or definition.timeout_seconds,
                }
            )
            return await self._repository.update(dataset_id, updated)
        if not isinstance(definition.query, SqlQuery):
            raise DatasetUpdateInvalid("Unsupported dataset query type.")
        if data.query is not None:
            raise DatasetUpdateInvalid("REST query is not valid for SQL datasets.")
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
                "fields": _apply_field_overrides(fields, overrides),
                "profile_overrides": overrides,
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
        if isinstance(definition.query, RestQuery):
            return await self._datasource_service.rest_query(
                dataset.data_source_id,
                query=definition.query,
                parameters=data.parameters,
                max_rows=definition.max_rows,
                timeout_seconds=definition.timeout_seconds,
                request_id=request_id,
            )
        raise ValueError("Unsupported dataset query type.")
