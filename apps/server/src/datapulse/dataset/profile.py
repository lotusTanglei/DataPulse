from __future__ import annotations

import json
from collections import Counter
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import Field, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dataset import (
    DatasetFieldOverride,
    DataType,
    FileQuery,
    RestQuery,
    SqlQuery,
)
from datapulse.dataset.repository import DatasetRepository
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.service import DatasourceService
from datapulse.filedata.inference import infer_type, infer_value, merge_types
from datapulse.filedata.parsers import parse_file
from datapulse.filedata.query import FileDatasetQueryService
from datapulse.filedata.repository import FileAssetRepository
from datapulse.query.models import QueryColumn, QueryRequest, QueryResult
from datapulse.query.safety import validate_read_only_sql


class FieldRole(StrEnum):
    IDENTIFIER = "identifier"
    DIMENSION = "dimension"
    MEASURE = "measure"
    GEOGRAPHY = "geography"
    TEMPORAL = "temporal"
    TEXT = "text"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


class DatasetFieldTopValue(ContractModel):
    value: JsonValue
    count: int = Field(ge=1)


class DatasetFieldProfile(ContractModel):
    name: NonBlankStr
    data_type: DataType
    role: FieldRole
    nullable: bool
    null_count: int = Field(default=0, ge=0)
    null_rate: float = Field(default=0, ge=0, le=1)
    unique_count: int = Field(default=0, ge=0)
    cardinality: int = Field(default=0, ge=0)
    uniqueness_ratio: float = Field(default=0, ge=0, le=1)
    min: JsonValue | None = None
    max: JsonValue | None = None
    top_values: tuple[DatasetFieldTopValue, ...] = Field(default_factory=tuple)
    sample_values: tuple[JsonValue, ...] = Field(default_factory=tuple)
    default_aggregation: str | None = None
    unit: str | None = None
    display_name: str | None = None


class DatasetProfile(ContractModel):
    dataset_id: NonBlankStr
    name: NonBlankStr
    row_count: int = Field(ge=0)
    sampled: bool
    fields: tuple[DatasetFieldProfile, ...] = Field(default_factory=tuple)
    time_coverage: tuple[JsonValue, JsonValue] | None = None
    suspected_primary_key: str | None = None
    candidate_time_fields: tuple[str, ...] = Field(default_factory=tuple)
    measure_candidates: tuple[str, ...] = Field(default_factory=tuple)
    geographic_fields: tuple[str, ...] = Field(default_factory=tuple)


class DatasetFieldProfilePatch(ContractModel):
    name: NonBlankStr
    data_type: DataType | None = None
    role: FieldRole | None = None
    default_aggregation: str | None = None
    unit: NonBlankStr | None = None
    display_name: NonBlankStr | None = None

    @model_validator(mode="after")
    def require_override(self) -> DatasetFieldProfilePatch:
        if (
            self.data_type is None
            and self.role is None
            and self.default_aggregation is None
            and self.unit is None
            and self.display_name is None
        ):
            raise ValueError("At least one field profile override is required.")
        return self


class DatasetProfilePatch(ContractModel):
    fields: tuple[DatasetFieldProfilePatch, ...] = Field(min_length=1)


def _query_rows(result: QueryResult) -> tuple[dict[str, JsonValue], ...]:
    names = [column.name for column in result.columns]
    rows: list[dict[str, JsonValue]] = []
    for values in result.rows:
        rows.append(
            {
                name: _json_value(infer_value(values[index]))
                for index, name in enumerate(names)
                if index < len(values)
            }
        )
    return tuple(rows)


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _column_type(data_type: str) -> DataType:
    if data_type in {"decimal", "float", "double", "numeric"}:
        return DataType.NUMBER
    try:
        return DataType(data_type)
    except ValueError:
        return DataType.STRING


def _name_suggests_identifier(name: str) -> bool:
    normalized = name.casefold().replace("-", "_").replace(" ", "_")
    tokens = {token for token in normalized.split("_") if token}
    return bool(
        tokens & {"id", "code", "key", "uuid", "identifier", "编号", "编码", "标识", "主键"}
        or normalized.endswith(("_id", "_code", "_key", "号"))
    )


def _name_suggests_geography(name: str) -> bool:
    normalized = name.casefold().replace("-", "_").replace(" ", "_")
    tokens = {token for token in normalized.split("_") if token}
    return bool(
        tokens
        & {
            "country",
            "province",
            "state",
            "city",
            "county",
            "district",
            "latitude",
            "longitude",
            "lat",
            "lon",
            "address",
            "postal",
            "zip",
            "国家",
            "省",
            "市",
            "县",
            "区",
            "地址",
            "经度",
            "纬度",
        }
        or normalized.endswith(("_province", "_city", "_county", "_district"))
    )


def _role(
    name: str,
    data_type: DataType,
    *,
    row_count: int,
    null_count: int,
    unique_count: int,
) -> FieldRole:
    observed = max(row_count - null_count, 0)
    ratio = unique_count / observed if observed else 0
    if _name_suggests_identifier(name) and observed > 0 and ratio >= 0.8:
        return FieldRole.IDENTIFIER
    if _name_suggests_geography(name):
        return FieldRole.GEOGRAPHY
    if data_type in {DataType.DATE, DataType.DATETIME}:
        return FieldRole.TEMPORAL
    if data_type is DataType.BOOLEAN:
        return FieldRole.BOOLEAN
    if data_type in {DataType.INTEGER, DataType.NUMBER}:
        return FieldRole.MEASURE
    if data_type is DataType.STRING:
        if observed == 0:
            return FieldRole.UNKNOWN
        return FieldRole.DIMENSION if unique_count <= max(20, observed // 2) else FieldRole.TEXT
    return FieldRole.UNKNOWN


def _top_values(values: list[JsonValue]) -> tuple[DatasetFieldTopValue, ...]:
    counts = Counter(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) for value in values
    )
    representatives: dict[str, JsonValue] = {}
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        representatives.setdefault(key, value)
    return tuple(
        DatasetFieldTopValue(value=representatives[key], count=count)
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    )


def _min_max(values: list[JsonValue]) -> tuple[JsonValue | None, JsonValue | None]:
    comparable = [value for value in values if not isinstance(value, bool)]
    if not comparable:
        return None, None
    try:
        return min(comparable), max(comparable)
    except TypeError:
        return None, None


def _override_map(
    overrides: tuple[DatasetFieldOverride, ...] | tuple[DatasetFieldProfilePatch, ...],
) -> dict[str, DatasetFieldOverride | DatasetFieldProfilePatch]:
    return {item.name: item for item in overrides}


class DatasetProfileService:
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

    async def _preview(self, dataset, *, max_rows: int) -> QueryResult:
        query = dataset.definition.query
        if isinstance(query, SqlQuery):
            source = await self._datasource_service.get(dataset.data_source_id)
            connector = self._registry.get(source.config.type)
            validate_read_only_sql(query.sql, connector.dialect)
            return await self._datasource_service.query(
                dataset.data_source_id,
                QueryRequest(
                    sql=query.sql,
                    parameters={
                        parameter.name: parameter.default
                        for parameter in dataset.definition.parameters
                    },
                    max_rows=min(max_rows, dataset.definition.max_rows),
                    timeout_seconds=dataset.definition.timeout_seconds,
                ),
                request_id=str(uuid4()),
                dataset_id=dataset.id,
                trigger="dataset-profile",
            )
        if isinstance(query, RestQuery):
            return await self._datasource_service.rest_query(
                dataset.data_source_id,
                query=query,
                parameters={
                    parameter.name: parameter.default
                    for parameter in dataset.definition.parameters
                },
                max_rows=min(max_rows, dataset.definition.max_rows),
                timeout_seconds=dataset.definition.timeout_seconds,
                request_id=str(uuid4()),
            )
        if isinstance(query, FileQuery):
            if self._file_asset_repository is None or self._file_query_service is None:
                raise RuntimeError("file dataset services are not configured")
            asset = await self._file_asset_repository.get(query.asset_id)
            parsed = await parse_file(
                Path(asset.storage_path),
                query.format,
                sheet_name=query.sheet_name,
                max_rows=min(max_rows, dataset.definition.max_rows),
            )
            return QueryResult(
                request_id=str(uuid4()),
                columns=tuple(
                    QueryColumn(name=field.name, data_type=field.data_type.value)
                    for field in parsed.fields
                ),
                rows=tuple(
                    tuple(row.get(field.name) for field in parsed.fields)
                    for row in parsed.sample_rows
                ),
                row_count=parsed.row_count,
                truncated=parsed.row_count > len(parsed.sample_rows),
                duration_ms=0,
            )
        raise ValueError("Unsupported dataset query type.")

    async def profile(
        self,
        dataset_id: str,
        *,
        max_rows: int = 5000,
        overrides: dict[str, DatasetFieldProfilePatch | DatasetFieldOverride] | None = None,
    ) -> DatasetProfile:
        dataset = await self._dataset_repository.get(dataset_id)
        result = await self._preview(dataset, max_rows=max_rows)
        rows = _query_rows(result)
        names = [column.name for column in result.columns]
        stored = _override_map(dataset.definition.profile_overrides)
        supplied = overrides or {}
        fields: list[DatasetFieldProfile] = []
        for index, name in enumerate(names):
            values = [row.get(name) for row in rows]
            non_null = [value for value in values if value is not None]
            unique_values: list[JsonValue] = []
            seen: set[str] = set()
            for value in non_null:
                key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                if key not in seen:
                    seen.add(key)
                    unique_values.append(value)
            data_type = _column_type(result.columns[index].data_type)
            if non_null:
                inferred = infer_type(non_null[0])
                for value in non_null[1:]:
                    candidate = infer_type(value)
                    if inferred == candidate:
                        continue
                    inferred = merge_types(inferred, candidate)
                if data_type is DataType.STRING and inferred is not DataType.STRING:
                    data_type = inferred
            base_role = _role(
                name,
                data_type,
                row_count=result.row_count,
                null_count=len(values) - len(non_null),
                unique_count=len(unique_values),
            )
            override = supplied.get(name) or stored.get(name)
            if isinstance(override, dict):
                override = DatasetFieldProfilePatch.model_validate({"name": name, **override})
            if override is not None:
                if override.data_type is not None:
                    data_type = override.data_type
                if override.role is not None:
                    base_role = FieldRole(override.role)
            minimum, maximum = _min_max(non_null)
            fields.append(
                DatasetFieldProfile(
                    name=name,
                    data_type=data_type,
                    role=base_role,
                    nullable=any(value is None for value in values),
                    null_count=len(values) - len(non_null),
                    null_rate=(len(values) - len(non_null)) / len(values) if values else 0,
                    unique_count=len(unique_values),
                    cardinality=len(unique_values),
                    uniqueness_ratio=(len(unique_values) / len(non_null) if non_null else 0),
                    min=minimum,
                    max=maximum,
                    top_values=_top_values(non_null),
                    sample_values=tuple(unique_values[:5]),
                    default_aggregation=(
                        override.default_aggregation if override is not None else None
                    ),
                    unit=override.unit if override is not None else None,
                    display_name=(
                        override.display_name if override is not None else None
                    ) or name,
                )
            )
        field_by_name = {field.name: field for field in fields}
        candidate_time_fields = tuple(
            field.name for field in fields if field.role is FieldRole.TEMPORAL
        )
        time_coverage = None
        if candidate_time_fields:
            time_field = field_by_name[candidate_time_fields[0]]
            if time_field.min is not None and time_field.max is not None:
                time_coverage = (time_field.min, time_field.max)
        suspected_primary_key = next(
            (field.name for field in fields if field.role is FieldRole.IDENTIFIER),
            None,
        )
        return DatasetProfile(
            dataset_id=dataset.id,
            name=dataset.name,
            row_count=result.row_count,
            sampled=result.truncated,
            fields=tuple(fields),
            time_coverage=time_coverage,
            suspected_primary_key=suspected_primary_key,
            candidate_time_fields=candidate_time_fields,
            measure_candidates=tuple(
                field.name for field in fields if field.role is FieldRole.MEASURE
            ),
            geographic_fields=tuple(
                field.name for field in fields if field.role is FieldRole.GEOGRAPHY
            ),
        )

    async def update(
        self,
        dataset_id: str,
        patch: DatasetProfilePatch,
    ) -> DatasetProfile:
        dataset = await self._dataset_repository.get(dataset_id)
        current = {item.name: item for item in dataset.definition.profile_overrides}
        for item in patch.fields:
            existing = current.get(item.name)
            data_type = item.data_type
            if data_type is None and existing is not None:
                data_type = existing.data_type
            role = item.role.value if item.role is not None else None
            if role is None and existing is not None:
                role = existing.role
            default_aggregation = item.default_aggregation
            if default_aggregation is None and existing is not None:
                default_aggregation = existing.default_aggregation
            unit = item.unit
            if unit is None and existing is not None:
                unit = existing.unit
            display_name = item.display_name
            if display_name is None and existing is not None:
                display_name = existing.display_name
            current[item.name] = DatasetFieldOverride(
                name=item.name,
                data_type=data_type,
                role=role,
                default_aggregation=default_aggregation,
                unit=unit,
                display_name=display_name,
            )
        known = {field.name for field in dataset.definition.fields}
        if any(name not in known for name in current):
            raise ValueError("The profile override references an unknown field.")
        overrides = tuple(current.values())
        data_types = {item.name: item.data_type for item in overrides if item.data_type is not None}
        definition = dataset.definition.model_copy(
            update={
                "fields": tuple(
                    field.model_copy(update={"data_type": data_types[field.name]})
                    if field.name in data_types
                    else field
                    for field in dataset.definition.fields
                ),
                "profile_overrides": overrides,
            }
        )
        await self._dataset_repository.update(dataset_id, definition)
        return await self.profile(dataset_id)


__all__ = [
    "DatasetFieldProfile",
    "DatasetFieldTopValue",
    "DatasetProfile",
    "DatasetProfilePatch",
    "DatasetProfileService",
    "FieldRole",
]
