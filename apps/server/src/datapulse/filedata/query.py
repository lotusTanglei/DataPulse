from collections.abc import Mapping
from typing import NamedTuple

from sqlglot import exp

from datapulse.contracts.chart import Aggregation, ChartSpec
from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import DatasetDefinition, FileQuery
from datapulse.filedata.duckdb_executor import DuckDBExecutor
from datapulse.query.models import QueryResult
from datapulse.screen.chart_query import (
    ChartQueryInvalid,
    _aggregate,
    _dimension_expressions,
    _effective_dimensions_and_filters,
    _field_expressions,
    _FilterCompiler,
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

        field_expressions = _field_expressions(dataset)
        metrics = {metric.name: metric for metric in dataset.semantics.metrics}
        requested_fields = {
            *spec.dimensions,
            *(bucket.field for bucket in spec.time_buckets),
            *(
                (level.field for level in spec.drill_down.levels)
                if spec.drill_down is not None
                else ()
            ),
            *(filter_.field for filter_ in spec.filters),
        }
        if not requested_fields <= set(field_expressions):
            raise ChartQueryInvalid("CHART_FIELD_UNKNOWN")
        for measure in spec.measures:
            metric = metrics.get(measure.field)
            if metric is None and measure.field not in field_expressions:
                raise ChartQueryInvalid("CHART_FIELD_UNKNOWN")
            if metric is not None and measure.aggregation.value != metric.aggregation:
                raise ChartQueryInvalid("CHART_METRIC_AGGREGATION_INVALID")
        measure_fields = {measure.field for measure in spec.measures}
        if any(
            sort.field not in field_expressions and sort.field not in measure_fields
            for sort in spec.sort
        ):
            raise ChartQueryInvalid("CHART_FIELD_UNKNOWN")

        query_parameters: dict[str, JsonValue] = {
            parameter.name: parameters.get(parameter.name, parameter.default)
            for parameter in dataset.parameters
        }
        filter_compiler = _FilterCompiler(
            parameters=query_parameters,
            runtime_parameters=parameters,
            field_expressions=field_expressions,
        )

        dimensions, filters = _effective_dimensions_and_filters(spec, parameters)
        dimension_expressions = _dimension_expressions(
            spec,
            dimensions,
            parameters,
            dialect="duckdb",
            field_expressions=field_expressions,
        )

        calculated_names = {field.name for field in dataset.semantics.calculated_fields}

        selections: list[exp.Expression] = [
            exp.alias_(dimension_expressions[field].copy(), field)
            if field in {bucket.field for bucket in spec.time_buckets} | calculated_names
            else dimension_expressions[field].copy()
            for field in dimensions
        ]
        measure_expressions: dict[str, exp.Expression] = {}
        for measure in spec.measures:
            metric = metrics.get(measure.field)
            source_field = metric.source_field if metric is not None else measure.field
            aggregation = (
                Aggregation(metric.aggregation) if metric is not None else measure.aggregation
            )
            aggregate = _aggregate(aggregation, field_expressions[source_field].copy())
            measure_expressions[measure.field] = aggregate
            selections.append(exp.alias_(aggregate.copy(), measure.field))
        query = (
            exp.select(*selections).from_("dataset_source").limit(min(spec.limit, dataset.max_rows))
        )
        if filters:
            conditions = [filter_compiler.compile(filter_) for filter_ in filters]
            condition = conditions[0]
            for next_condition in conditions[1:]:
                condition = exp.and_(condition, next_condition)
            query = query.where(condition)
        if spec.measures and dimensions:
            query = query.group_by(*(dimension_expressions[field].copy() for field in dimensions))
        for sort in spec.sort:
            sort_expression = (
                measure_expressions[sort.field].copy()
                if sort.field in measure_expressions
                else dimension_expressions.get(sort.field, field_expressions[sort.field]).copy()
            )
            query = query.order_by(
                exp.Ordered(
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

    async def preview(
        self,
        *,
        request_id: str,
        source_path,
        max_rows: int,
        timeout_seconds: int,
    ) -> QueryResult:
        return await self._executor.execute(
            f"SELECT * FROM dataset_source LIMIT {max_rows}",
            (),
            source_path=source_path,
            request_id=request_id,
            timeout_seconds=min(timeout_seconds, self._executor.timeout_seconds),
            max_rows=max_rows,
        )
