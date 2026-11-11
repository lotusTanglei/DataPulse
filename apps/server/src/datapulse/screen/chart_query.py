from collections.abc import Mapping, Sequence

from sqlglot import exp

from datapulse.contracts.chart import (
    Aggregation,
    ChartSpec,
    ChartType,
    Filter,
    FilterOperator,
    LiteralValue,
    ParameterRef,
    TimeBucket,
)
from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import (
    CalculationOperator,
    DatasetDefinition,
    SqlQuery,
    TimeGrain,
)
from datapulse.query.models import QueryRequest


class ChartQueryInvalid(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _column(field: str) -> exp.Column:
    return exp.column(field, table="dataset_source")


def _aggregate(
    aggregation: Aggregation,
    expression: exp.Expression,
) -> exp.Expression:
    aggregate_types: dict[Aggregation, type[exp.AggFunc]] = {
        Aggregation.SUM: exp.Sum,
        Aggregation.AVERAGE: exp.Avg,
        Aggregation.MINIMUM: exp.Min,
        Aggregation.MAXIMUM: exp.Max,
        Aggregation.COUNT: exp.Count,
    }
    return aggregate_types[aggregation](this=expression)


def _field_expressions(dataset: DatasetDefinition) -> dict[str, exp.Expression]:
    expressions: dict[str, exp.Expression] = {
        field.name: _column(field.name) for field in dataset.fields
    }
    operator_types: dict[CalculationOperator, type[exp.Binary]] = {
        CalculationOperator.ADD: exp.Add,
        CalculationOperator.SUBTRACT: exp.Sub,
        CalculationOperator.MULTIPLY: exp.Mul,
        CalculationOperator.DIVIDE: exp.Div,
    }
    for field in dataset.semantics.calculated_fields:
        definition = field.expression
        left = expressions.get(definition.left_field)
        right = (
            expressions.get(definition.right_field)
            if definition.right_field is not None
            else exp.Literal.number(definition.constant)
        )
        if left is None or right is None:
            raise ChartQueryInvalid("CHART_SEMANTIC_FIELD_INVALID")
        expressions[field.name] = operator_types[definition.operator](
            this=left.copy(),
            expression=right.copy(),
        )
    return expressions


def _resolve_grain(bucket: TimeBucket, parameters: Mapping[str, JsonValue]) -> TimeGrain:
    if bucket.grain is not None:
        return bucket.grain
    assert bucket.parameter is not None
    value = parameters.get(bucket.parameter)
    try:
        return TimeGrain(value)
    except (TypeError, ValueError) as error:
        raise ChartQueryInvalid("CHART_TIME_GRAIN_INVALID") from error


def _time_bucket_expression(
    expression: exp.Expression,
    grain: TimeGrain,
    *,
    dialect: str | None,
) -> exp.Expression:
    column = expression.copy()
    if dialect == "sqlite":
        formats = {
            TimeGrain.YEAR: "%Y-01-01",
            TimeGrain.MONTH: "%Y-%m-01",
            TimeGrain.WEEK: "%Y-W%W",
            TimeGrain.DAY: "%Y-%m-%d",
            TimeGrain.HOUR: "%Y-%m-%d %H:00:00",
        }
        if grain is TimeGrain.QUARTER:
            year = exp.Anonymous(
                this="STRFTIME",
                expressions=[exp.Literal.string("%Y"), column.copy()],
            )
            month = exp.cast(
                exp.Anonymous(
                    this="STRFTIME",
                    expressions=[exp.Literal.string("%m"), column.copy()],
                ),
                "INTEGER",
            )
            quarter = exp.Div(
                this=exp.Add(this=month, expression=exp.Literal.number(2)),
                expression=exp.Literal.number(3),
            )
            return exp.Anonymous(
                this="PRINTF",
                expressions=[exp.Literal.string("%s-Q%d"), year, quarter],
            )
        return exp.Anonymous(
            this="STRFTIME",
            expressions=[exp.Literal.string(formats[grain]), column],
        )
    return exp.DateTrunc(
        unit=exp.Literal.string(grain.value),
        this=column,
    )


def _effective_dimensions_and_filters(
    spec: ChartSpec,
    parameters: Mapping[str, JsonValue],
) -> tuple[tuple[str, ...], tuple[Filter, ...]]:
    if spec.drill_down is None:
        return spec.dimensions, spec.filters
    raw_level = parameters.get(spec.drill_down.level_parameter)
    if isinstance(raw_level, bool) or not isinstance(raw_level, int):
        raise ChartQueryInvalid("CHART_DRILL_LEVEL_INVALID")
    if raw_level < 0 or raw_level >= len(spec.drill_down.levels):
        raise ChartQueryInvalid("CHART_DRILL_LEVEL_INVALID")
    root_field = spec.drill_down.levels[0].field
    current_field = spec.drill_down.levels[raw_level].field
    dimensions = tuple(current_field if field == root_field else field for field in spec.dimensions)
    drill_filters = tuple(
        Filter(
            field=level.field,
            operator=FilterOperator.EQUALS,
            value=ParameterRef(name=level.selection_parameter),
        )
        for level in spec.drill_down.levels[:raw_level]
    )
    return dimensions, (*spec.filters, *drill_filters)


def _dimension_expressions(
    spec: ChartSpec,
    dimensions: tuple[str, ...],
    parameters: Mapping[str, JsonValue],
    *,
    dialect: str | None,
    field_expressions: Mapping[str, exp.Expression],
) -> dict[str, exp.Expression]:
    buckets = {bucket.field: bucket for bucket in spec.time_buckets}
    return {
        field: (
            _time_bucket_expression(
                field_expressions[field],
                _resolve_grain(buckets[field], parameters),
                dialect=dialect,
            )
            if field in buckets
            else field_expressions[field].copy()
        )
        for field in dimensions
    }


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
        field_expressions: Mapping[str, exp.Expression],
    ) -> None:
        self.parameters = parameters
        self.runtime_parameters = runtime_parameters
        self.field_expressions = field_expressions
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
        column = self.field_expressions[filter_.field].copy()
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
            dialect=dialect,
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
        query = exp.select(*selections).from_("dataset_source")
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
