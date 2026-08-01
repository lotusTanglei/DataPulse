from collections.abc import Mapping
from typing import NamedTuple

from datapulse.contracts.chart import ChartSpec
from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import DatasetDefinition, FileQuery
from datapulse.filedata.duckdb_executor import DuckDBExecutor
from datapulse.query.models import QueryResult
from datapulse.screen.chart_query import (
    ChartQueryInvalid,
    _FilterCompiler,
    _aggregate,
    _column,
    _validate_visual,
)


class CompiledFileQuery(NamedTuple):
    sql: str
    parameters: tuple[JsonValue, ...]


def _to_duckdb_sql(sql: str, parameters: dict[str, JsonValue]) -> CompiledFileQuery:
    ordered_values: list[JsonValue] = []
    for name, value in parameters.items():
        sql = sql.replace(f":{name}", "?", 1)
        ordered_values.append(value)
    return CompiledFileQuery(sql=sql, parameters=tuple(ordered_values))


class FileQueryCompiler:
    def compile(
        self,
        spec: ChartSpec,
        dataset: DatasetDefinition,
        source_path,
        parameters: Mapping[str, JsonValue],
    ) -> CompiledFileQuery:
        del source_path
        if spec.dataset_id != dataset.id:
            raise ChartQueryInvalid("CHART_DATASET_MISMATCH")
        if not isinstance(dataset.query, FileQuery):
            raise ChartQueryInvalid("CHART_DATASET_UNSUPPORTED")
        _validate_visual(spec)

        known_fields = {field.name for field in dataset.fields}
        requested_fields = {
            *spec.dimensions,
            *(measure.field for measure in spec.measures),
            *(filter_.field for filter_ in spec.filters),
            *(sort.field for sort in spec.sort),
        }
        if not requested_fields <= known_fields:
            raise ChartQueryInvalid("CHART_FIELD_UNKNOWN")

        query_parameters: dict[str, JsonValue] = {
            parameter.name: parameters.get(parameter.name, parameter.default)
            for parameter in dataset.parameters
        }
        filter_compiler = _FilterCompiler(
            parameters=query_parameters,
            runtime_parameters=parameters,
        )

        selections = [_column(field) for field in spec.dimensions]
        selections.extend(_aggregate(measure).as_(measure.field) for measure in spec.measures)
        query = (
            __import__("sqlglot").exp.select(*selections)
            .from_("dataset_source")
            .limit(min(spec.limit, dataset.max_rows))
        )
        if spec.filters:
            conditions = [filter_compiler.compile(filter_) for filter_ in spec.filters]
            condition = conditions[0]
            for next_condition in conditions[1:]:
                condition = __import__("sqlglot").exp.and_(condition, next_condition)
            query = query.where(condition)
        if spec.measures and spec.dimensions:
            query = query.group_by(*(_column(field) for field in spec.dimensions))
        measures_by_field = {measure.field: measure for measure in spec.measures}
        for sort in spec.sort:
            sort_expression = (
                _aggregate(measures_by_field[sort.field])
                if sort.field in measures_by_field
                else _column(sort.field)
            )
            query = query.order_by(
                __import__("sqlglot").exp.Ordered(
                    this=sort_expression,
                    desc=sort.direction.value == "desc",
                ),
                append=True,
            )
        return _to_duckdb_sql(query.sql(), query_parameters)


class FileDatasetQueryService:
    def __init__(
        self,
        *,
        compiler: FileQueryCompiler,
        executor: DuckDBExecutor,
    ) -> None:
        self._compiler = compiler
        self._executor = executor

    async def query(
        self,
        *,
        dataset: DatasetDefinition,
        chart_spec: ChartSpec,
        parameters: Mapping[str, JsonValue],
        request_id: str,
        source_path,
    ) -> QueryResult:
        compiled = self._compiler.compile(
            spec=chart_spec,
            dataset=dataset,
            source_path=source_path,
            parameters=parameters,
        )
        return await self._executor.execute(
            compiled.sql,
            compiled.parameters,
            source_path=source_path,
            request_id=request_id,
            timeout_seconds=min(dataset.timeout_seconds, self._executor.timeout_seconds),
            max_rows=min(chart_spec.limit, dataset.max_rows),
        )
