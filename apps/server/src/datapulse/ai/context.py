from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from datapulse.ai.models import DatasetContext, DatasetContextField
from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import DatasetField, FileQuery, RestQuery, SqlQuery
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.profile import DatasetFieldProfile, DatasetProfile, DatasetProfileService
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
        rendered.append({columns[index]: _truncate(value) for index, value in enumerate(row)})
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
        profile_service: DatasetProfileService | None = None,
        max_context_fields: int = 50,
        max_context_chars: int = 12_000,
    ) -> None:
        self._dataset_repository = dataset_repository
        self._datasource_service = datasource_service
        self._registry = registry
        self._file_asset_repository = file_asset_repository
        self._file_query_service = file_query_service
        self._profile_service = profile_service
        self._max_context_fields = max_context_fields
        self._max_context_chars = max_context_chars

    async def _preview_sql(self, dataset: DatasetResponse, *, max_rows: int) -> QueryResult:
        source = await self._datasource_service.get(dataset.data_source_id)
        connector = self._registry.get(source.config.type)
        validate_read_only_sql(dataset.definition.query.sql, connector.dialect)
        return await self._datasource_service.query(
            dataset.data_source_id,
            QueryRequest(
                sql=dataset.definition.query.sql,
                parameters={
                    parameter.name: parameter.default for parameter in dataset.definition.parameters
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

    async def _preview_rest(self, dataset: DatasetResponse, *, max_rows: int) -> QueryResult:
        query = dataset.definition.query
        if not isinstance(query, RestQuery):
            raise RuntimeError("REST dataset query is invalid")
        return await self._datasource_service.rest_query(
            dataset.data_source_id,
            query,
            parameters={
                parameter.name: parameter.default for parameter in dataset.definition.parameters
            },
            max_rows=min(max_rows, dataset.definition.max_rows),
            timeout_seconds=dataset.definition.timeout_seconds,
            request_id=str(uuid4()),
        )

    async def build(
        self,
        dataset_ids: tuple[str, ...],
        *,
        max_rows: int,
        question: str | None = None,
        include_samples: bool = False,
    ) -> tuple[DatasetContext, ...]:
        contexts: list[DatasetContext] = []
        for dataset_id in dataset_ids:
            dataset = await self._dataset_repository.get(dataset_id)
            profile = (
                await self._profile_service.profile(dataset_id)
                if self._profile_service is not None
                else None
            )
            preview = None
            if include_samples or profile is None:
                if isinstance(dataset.definition.query, SqlQuery):
                    preview = await self._preview_sql(dataset, max_rows=max_rows)
                elif isinstance(dataset.definition.query, FileQuery):
                    preview = await self._preview_file(dataset, max_rows=max_rows)
                elif isinstance(dataset.definition.query, RestQuery):
                    preview = await self._preview_rest(dataset, max_rows=max_rows)
                else:
                    raise ValueError("Unsupported dataset query type.")
            if profile is not None:
                field_limit = _select_profile_fields(
                    profile.fields,
                    question=question,
                    max_fields=self._max_context_fields,
                )
                profile_summary = _profile_summary(profile)
            else:
                field_limit = tuple(dataset.definition.fields[: self._max_context_fields])
                profile_summary = ""
            field_names = tuple(field.name for field in field_limit)
            sample_rows = (
                tuple(
                    {
                        name: row.get(name)
                        for name in field_names
                        if name in row
                    }
                    for row in _rows(preview)[:max_rows]
                )
                if preview is not None
                else ()
            )
            field_limit, sample_rows, profile_summary, clipped = _fit_budget(
                field_limit,
                sample_rows,
                profile_summary,
                max_chars=self._max_context_chars,
            )
            contexts.append(
                DatasetContext(
                    dataset_id=dataset.id,
                    name=dataset.name,
                    fields=tuple(
                        _context_field(field)
                        for field in field_limit
                    ),
                    sample_rows=sample_rows,
                    summary=(
                        f"{len(field_limit)} fields; "
                        f"{len(sample_rows)} sample rows; "
                        f"{len(dataset.definition.parameters)} parameters."
                        + (" budget clipped." if clipped else "")
                    ),
                    profile_summary=profile_summary,
                )
            )
        return tuple(contexts)


__all__ = ["DatasetContextService"]


def _fit_budget(
    fields,
    rows: tuple[dict[str, JsonValue], ...],
    profile_summary: str,
    *,
    max_chars: int,
):
    selected_fields = list(fields)
    selected_rows = list(rows)
    clipped = False

    def serialized_size() -> int:
        return len(
            json.dumps(
                {
                    "fields": [field.model_dump(mode="json") for field in selected_fields],
                    "rows": selected_rows,
                    "profile_summary": profile_summary,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

    while serialized_size() > max_chars and selected_rows:
        selected_rows.pop()
        clipped = True
    while serialized_size() > max_chars and selected_fields:
        selected_fields.pop()
        allowed = {field.name for field in selected_fields}
        selected_rows = [
            {name: value for name, value in row.items() if name in allowed}
            for row in selected_rows
        ]
        clipped = True
    while serialized_size() > max_chars and profile_summary:
        profile_summary = profile_summary[:- max(1, len(profile_summary) // 5)]
        clipped = True
    return tuple(selected_fields), tuple(selected_rows), profile_summary, clipped


def _select_profile_fields(
    fields: tuple[DatasetFieldProfile, ...],
    *,
    question: str | None,
    max_fields: int,
) -> tuple[DatasetFieldProfile, ...]:
    if not fields:
        return ()
    ordered = list(fields)
    if question:
        lowered = question.casefold()
        mentioned = [field for field in ordered if field.name.casefold() in lowered]
        if mentioned:
            ordered = mentioned
        else:
            ordered = [
                field
                for field in ordered
                if field.role.value in {"dimension", "measure", "temporal", "geography"}
            ] or ordered
    return tuple(ordered[:max_fields])


def _profile_summary(profile: DatasetProfile) -> str:
    pieces = [f"{profile.row_count} rows"]
    if profile.sampled:
        pieces.append("sampled")
    if profile.time_coverage is not None:
        pieces.append(f"time={profile.time_coverage[0]}..{profile.time_coverage[1]}")
    if profile.suspected_primary_key is not None:
        pieces.append(f"primary_key={profile.suspected_primary_key}")
    if profile.measure_candidates:
        pieces.append(f"measures={','.join(profile.measure_candidates)}")
    if profile.geographic_fields:
        pieces.append(f"geography={','.join(profile.geographic_fields)}")
    return "; ".join(pieces)


def _context_field(field: DatasetField | DatasetFieldProfile) -> DatasetContextField:
    if isinstance(field, DatasetFieldProfile):
        return DatasetContextField(
            name=field.name,
            data_type=field.data_type.value,
            role=field.role.value,
            cardinality=field.cardinality,
            null_rate=field.null_rate,
        )
    return DatasetContextField(name=field.name, data_type=field.data_type.value)
