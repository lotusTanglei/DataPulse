from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from datapulse.ai.models import DatasetContext, DatasetContextField
from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import FileQuery, SqlQuery
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import DatasetRepository
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.service import DatasourceService
from datapulse.filedata.parsers import parse_file
from datapulse.filedata.query import FileDatasetQueryService
from datapulse.filedata.repository import FileAssetRepository
from datapulse.query.models import QueryRequest, QueryResult
from datapulse.query.safety import validate_read_only_sql


def _truncate(value: JsonValue) -> JsonValue:
    if isinstance(value, str) and len(value) > 120:
        return f"{value[:117]}..."
    return value


def _rows(result: QueryResult) -> tuple[dict[str, JsonValue], ...]:
    columns = [column.name for column in result.columns]
    rendered: list[dict[str, JsonValue]] = []
    for row in result.rows:
        rendered.append(
            {
                columns[index]: _truncate(value)
                for index, value in enumerate(row)
            }
        )
    return tuple(rendered)


class DatasetContextService:
    def __init__(
        self,
        *,
        dataset_repository: DatasetRepository,
        datasource_service: DatasourceService,
        registry: ConnectorRegistry,
        file_asset_repository: FileAssetRepository | None = None,
        file_query_service: FileDatasetQueryService | None = None,
    ) -> None:
        self._dataset_repository = dataset_repository
        self._datasource_service = datasource_service
        self._registry = registry
        self._file_asset_repository = file_asset_repository
        self._file_query_service = file_query_service

    async def _preview_sql(self, dataset: DatasetResponse, *, max_rows: int) -> QueryResult:
        source = await self._datasource_service.get(dataset.data_source_id)
        connector = self._registry.get(source.config.type)
        validate_read_only_sql(dataset.definition.query.sql, connector.dialect)
        return await self._datasource_service.query(
            dataset.data_source_id,
            QueryRequest(
                sql=dataset.definition.query.sql,
                parameters={
                    parameter.name: parameter.default
                    for parameter in dataset.definition.parameters
                },
                max_rows=min(max_rows, dataset.definition.max_rows),
                timeout_seconds=dataset.definition.timeout_seconds,
            ),
            request_id=str(uuid4()),
            dataset_id=dataset.id,
            trigger="ai-context",
        )

    async def _preview_file(self, dataset: DatasetResponse, *, max_rows: int) -> QueryResult:
        if self._file_asset_repository is None or self._file_query_service is None:
            raise RuntimeError("file dataset services are not configured")
        query = dataset.definition.query
        if not isinstance(query, FileQuery):
            raise RuntimeError("file dataset query is invalid")
        asset = await self._file_asset_repository.get(query.asset_id)
        parsed = await parse_file(
            Path(asset.storage_path),
            query.format,
            sheet_name=query.sheet_name,
            max_rows=min(max_rows, dataset.definition.max_rows),
        )
        return await self._file_query_service.preview(
            request_id=str(uuid4()),
            source_path=parsed.normalized_path,
            max_rows=min(max_rows, dataset.definition.max_rows),
            timeout_seconds=dataset.definition.timeout_seconds,
        )

    async def build(
        self,
        dataset_ids: tuple[str, ...],
        *,
        max_rows: int,
    ) -> tuple[DatasetContext, ...]:
        contexts: list[DatasetContext] = []
        for dataset_id in dataset_ids:
            dataset = await self._dataset_repository.get(dataset_id)
            if isinstance(dataset.definition.query, SqlQuery):
                preview = await self._preview_sql(dataset, max_rows=max_rows)
            elif isinstance(dataset.definition.query, FileQuery):
                preview = await self._preview_file(dataset, max_rows=max_rows)
            else:
                raise ValueError("Unsupported dataset query type.")
            field_limit = dataset.definition.fields[:50]
            sample_rows = _rows(preview)[:max_rows]
            contexts.append(
                DatasetContext(
                    dataset_id=dataset.id,
                    name=dataset.name,
                    fields=tuple(
                        DatasetContextField(
                            name=field.name,
                            data_type=field.data_type.value,
                        )
                        for field in field_limit
                    ),
                    sample_rows=sample_rows,
                    summary=(
                        f"{len(field_limit)} fields; "
                        f"{len(sample_rows)} sample rows; "
                        f"{len(dataset.definition.parameters)} parameters."
                    ),
                )
            )
        return tuple(contexts)


__all__ = ["DatasetContextService"]
