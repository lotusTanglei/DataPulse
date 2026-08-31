from collections.abc import Mapping, Sequence

from sqlglot import exp

from datapulse.contracts.chart import (
    Aggregation,
    ChartSpec,
    ChartType,
    Filter,
    FilterOperator,
    LiteralValue,
    Measure,
    ParameterRef,
)
from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import DatasetDefinition, SqlQuery
from datapulse.query.models import QueryRequest


class ChartQueryInvalid(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _column(field: str) -> exp.Column:
    return exp.column(field, table="dataset_source")


def _aggregate(measure: Measure) -> exp.Expression:
    column = _column(measure.field)
    aggregate_types: dict[Aggregation, type[exp.AggFunc]] = {
        Aggregation.SUM: exp.Sum,
        Aggregation.AVERAGE: exp.Avg,
        Aggregation.MINIMUM: exp.Min,
        Aggregation.MAXIMUM: exp.Max,
        Aggregation.COUNT: exp.Count,
    }
    return aggregate_types[measure.aggregation](this=column)


def _validate_visual(spec: ChartSpec) -> None:
    visual_type = spec.visual.type
    dimension_count = len(spec.dimensions)
    measure_count = len(spec.measures)
    valid = True
    if visual_type in {
        ChartType.LINE,
        ChartType.AREA,
        ChartType.BAR,
        ChartType.RADAR,
        ChartType.HEATMAP,
        ChartType.SCATTER,
        ChartType.FUNNEL,
    }:
        valid = dimension_count >= 1 and measure_count >= 1
    elif visual_type in {ChartType.PIE, ChartType.MAP}:
        valid = dimension_count == 1 and measure_count >= 1
    elif visual_type in {ChartType.KPI, ChartType.PROGRESS, ChartType.GAUGE}:
        valid = dimension_count <= 1 and measure_count == 1
    elif visual_type is ChartType.TABLE:
        valid = dimension_count + measure_count >= 1
    if not valid:
        raise ChartQueryInvalid("CHART_VISUAL_INVALID")


class _FilterCompiler:
    def __init__(
        self,
        *,
        parameters: dict[str, JsonValue],
        runtime_parameters: Mapping[str, JsonValue],
    ) -> None:
        self.parameters = parameters
        self.runtime_parameters = runtime_parameters
        self._next_index = 0

    def _bind(self, value: JsonValue) -> exp.Placeholder:
        while True:
            name = f"chart_filter_{self._next_index}"
            self._next_index += 1
            if name not in self.parameters:
                self.parameters[name] = value
                return exp.Placeholder(this=name)

    def _value(self, filter_: Filter) -> JsonValue:
        value = filter_.value
        if isinstance(value, ParameterRef):
            if value.name not in self.runtime_parameters:
                raise ChartQueryInvalid("CHART_PARAMETER_MISSING")
            return self.runtime_parameters[value.name]
        if isinstance(value, LiteralValue):
            return value.value
        raise ChartQueryInvalid("CHART_FILTER_VALUE_INVALID")

    def compile(self, filter_: Filter) -> exp.Expression:
        column = _column(filter_.field)
        operator = filter_.operator
        if operator is FilterOperator.IS_NULL:
            return exp.Is(this=column, expression=exp.Null())
        if operator is FilterOperator.IS_NOT_NULL:
            return exp.Is(this=column, expression=exp.Null(), negate=True)

        value = self._value(filter_)
        if operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
            if (
                not isinstance(value, Sequence)
                or isinstance(value, (str, bytes, bytearray))
                or not value
            ):
                raise ChartQueryInvalid("CHART_FILTER_VALUE_INVALID")
            expression = exp.In(this=column, expressions=[self._bind(item) for item in value])
            return exp.Not(this=expression) if operator is FilterOperator.NOT_IN else expression
        if operator is FilterOperator.BETWEEN:
            if (
                not isinstance(value, Sequence)
                or isinstance(value, (str, bytes, bytearray))
                or len(value) != 2
            ):
                raise ChartQueryInvalid("CHART_FILTER_VALUE_INVALID")
            return exp.Between(
                this=column,
                low=self._bind(value[0]),
                high=self._bind(value[1]),
            )
        if operator is FilterOperator.CONTAINS:
            if not isinstance(value, str):
                raise ChartQueryInvalid("CHART_FILTER_VALUE_INVALID")
            return exp.Like(this=column, expression=self._bind(f"%{value}%"))

        placeholder = self._bind(value)
        binary_types: dict[FilterOperator, type[exp.Binary]] = {
            FilterOperator.EQUALS: exp.EQ,
            FilterOperator.NOT_EQUALS: exp.NEQ,
            FilterOperator.GREATER_THAN: exp.GT,
            FilterOperator.GREATER_THAN_OR_EQUAL: exp.GTE,
            FilterOperator.LESS_THAN: exp.LT,
            FilterOperator.LESS_THAN_OR_EQUAL: exp.LTE,
        }
        binary_type = binary_types.get(operator)
        if binary_type is None:
            raise ChartQueryInvalid("CHART_FILTER_VALUE_INVALID")
        return binary_type(this=column, expression=placeholder)


class ChartQueryCompiler:
    def compile(
        self,
        spec: ChartSpec,
        dataset: DatasetDefinition,
        parameters: Mapping[str, JsonValue],
        dialect: str | None = None,
    ) -> QueryRequest:
        if spec.dataset_id != dataset.id:
            raise ChartQueryInvalid("CHART_DATASET_MISMATCH")
        if not isinstance(dataset.query, SqlQuery):
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

        selections: list[exp.Expression] = [_column(field) for field in spec.dimensions]
        selections.extend(
            exp.alias_(_aggregate(measure), measure.field) for measure in spec.measures
        )
        query = exp.select(*selections).from_("dataset_source")
        if spec.filters:
            conditions = [filter_compiler.compile(filter_) for filter_ in spec.filters]
            condition = conditions[0]
            for next_condition in conditions[1:]:
                condition = exp.and_(condition, next_condition)
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
                exp.Ordered(
                    this=sort_expression,
                    desc=sort.direction.value == "desc",
                ),
                append=True,
            )
        query = query.limit(spec.limit)
        # MySQL/MariaDB require backticks when ANSI_QUOTES is not enabled.
        # Keep SQLAlchemy-style named placeholders for the other dialects;
        # sqlglot's PostgreSQL renderer would otherwise rewrite them.
        output_dialect = "mysql" if dialect == "mysql" else None
        outer_sql = query.sql(dialect=output_dialect)
        source_marker = "FROM dataset_source"
        if source_marker not in outer_sql:
            raise ChartQueryInvalid("CHART_QUERY_BUILD_FAILED")
        sql = outer_sql.replace(
            source_marker,
            f"FROM ({dataset.query.sql}) AS dataset_source",
            1,
        )
        return QueryRequest(
            sql=sql,
            parameters=query_parameters,
            max_rows=spec.limit,
            timeout_seconds=dataset.timeout_seconds,
        )


__all__ = ["ChartQueryCompiler", "ChartQueryInvalid"]
