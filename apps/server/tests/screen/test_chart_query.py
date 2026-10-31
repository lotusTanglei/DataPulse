import pytest

from datapulse.contracts.chart import (
    Aggregation,
    ChartSpec,
    ChartType,
    Filter,
    FilterOperator,
    LiteralValue,
    Measure,
    ParameterRef,
    Sort,
    SortDirection,
    VisualSpec,
)
from datapulse.contracts.dataset import (
    DatasetDefinition,
    DatasetField,
    DatasetParameter,
    DataType,
    SqlQuery,
)
from datapulse.screen.chart_query import ChartQueryCompiler, ChartQueryInvalid


def sql_dataset(sql: str = "SELECT month, amount, region FROM sales") -> DatasetDefinition:
    return DatasetDefinition(
        id="sales",
        name="Sales",
        data_source_id="source-1",
        query=SqlQuery(sql=sql),
        fields=(
            DatasetField(name="month", data_type=DataType.STRING),
            DatasetField(name="amount", data_type=DataType.NUMBER),
            DatasetField(name="region", data_type=DataType.STRING),
        ),
    )


def line_spec(
    *,
    filters: tuple[Filter, ...] = (),
    sort: tuple[Sort, ...] = (),
    limit: int = 1000,
) -> ChartSpec:
    return ChartSpec(
        dataset_id="sales",
        dimensions=("month",),
        measures=(Measure(field="amount", aggregation=Aggregation.SUM),),
        filters=filters,
        sort=sort,
        limit=limit,
        visual=VisualSpec(type=ChartType.LINE),
    )


def test_compiler_wraps_dataset_and_binds_filter_values() -> None:
    compiled = ChartQueryCompiler().compile(
        spec=line_spec(
            filters=(
                Filter(
                    field="region",
                    operator=FilterOperator.EQUALS,
                    value=ParameterRef(name="region"),
                ),
            )
        ),
        dataset=sql_dataset(),
        parameters={"region": "east"},
    )

    assert compiled.sql.startswith("SELECT")
    assert "FROM (SELECT month, amount, region FROM sales)" in compiled.sql
    assert "SUM(dataset_source.amount)" in compiled.sql
    assert "GROUP BY dataset_source.month" in compiled.sql
    assert compiled.parameters["chart_filter_0"] == "east"
    assert "east" not in compiled.sql
    assert ":chart_filter_0" in compiled.sql


def test_compiler_uses_mysql_identifier_quotes_for_non_ascii_fields() -> None:
    dataset = DatasetDefinition(
        id="departments",
        name="Departments",
        data_source_id="source-1",
        query=SqlQuery(sql="SELECT name AS '名称', code AS '编码' FROM departments"),
        fields=(
            DatasetField(name="名称", data_type=DataType.STRING),
            DatasetField(name="编码", data_type=DataType.STRING),
        ),
    )
    spec = ChartSpec(
        dataset_id="departments",
        dimensions=("名称",),
        measures=(Measure(field="编码", aggregation=Aggregation.SUM),),
        visual=VisualSpec(type=ChartType.TABLE),
    )

    compiled = ChartQueryCompiler().compile(
        spec=spec,
        dataset=dataset,
        parameters={},
        dialect="mysql",
    )

    assert "dataset_source.`名称`" in compiled.sql
    assert "SUM(dataset_source.`编码`) AS `编码`" in compiled.sql
    assert 'dataset_source."名称"' not in compiled.sql


def test_compiler_merges_dataset_defaults_and_avoids_parameter_collisions() -> None:
    dataset = sql_dataset(
        "SELECT month, amount, region FROM sales WHERE tenant = :chart_filter_0"
    ).model_copy(
        update={
            "parameters": (
                DatasetParameter(
                    name="chart_filter_0",
                    data_type=DataType.STRING,
                    default="tenant-a",
                ),
            )
        }
    )
    compiled = ChartQueryCompiler().compile(
        spec=line_spec(
            filters=(
                Filter(
                    field="region",
                    operator=FilterOperator.EQUALS,
                    value=LiteralValue(value="east"),
                ),
            )
        ),
        dataset=dataset,
        parameters={},
    )

    assert compiled.parameters == {
        "chart_filter_0": "tenant-a",
        "chart_filter_1": "east",
    }
    assert ":chart_filter_1" in compiled.sql


@pytest.mark.parametrize(
    ("operator", "value", "expected_values"),
    [
        (FilterOperator.IN, ["east", "west"], ("east", "west")),
        (FilterOperator.NOT_IN, ["east", "west"], ("east", "west")),
        (FilterOperator.BETWEEN, [10, 20], (10, 20)),
    ],
)
def test_compiler_expands_multi_value_filters_into_bound_parameters(
    operator: FilterOperator,
    value: list[object],
    expected_values: tuple[object, ...],
) -> None:
    compiled = ChartQueryCompiler().compile(
        spec=line_spec(
            filters=(
                Filter(
                    field="amount" if operator is FilterOperator.BETWEEN else "region",
                    operator=operator,
                    value=LiteralValue(value=value),
                ),
            )
        ),
        dataset=sql_dataset(),
        parameters={},
    )

    assert tuple(compiled.parameters.values()) == expected_values
    assert "'east'" not in compiled.sql
    assert "'west'" not in compiled.sql
    assert "BETWEEN 10 AND 20" not in compiled.sql
    assert ":chart_filter_0" in compiled.sql


@pytest.mark.parametrize(
    "operator",
    [FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL],
)
def test_compiler_null_filters_do_not_create_parameters(
    operator: FilterOperator,
) -> None:
    compiled = ChartQueryCompiler().compile(
        spec=line_spec(
            filters=(
                Filter(
                    field="region",
                    operator=operator,
                    value=LiteralValue(),
                ),
            )
        ),
        dataset=sql_dataset(),
        parameters={},
    )

    assert compiled.parameters == {}
    assert "IS NULL" in compiled.sql or "IS NOT NULL" in compiled.sql


def test_compiler_emits_aggregation_sort_and_limit() -> None:
    spec = ChartSpec(
        dataset_id="sales",
        dimensions=("region",),
        measures=(
            Measure(field="amount", aggregation=Aggregation.AVERAGE),
            Measure(field="month", aggregation=Aggregation.COUNT),
        ),
        sort=(Sort(field="amount", direction=SortDirection.DESCENDING),),
        limit=25,
        visual=VisualSpec(type=ChartType.BAR),
    )

    compiled = ChartQueryCompiler().compile(
        spec=spec,
        dataset=sql_dataset(),
        parameters={},
    )

    assert "AVG(dataset_source.amount)" in compiled.sql
    assert "COUNT(dataset_source.month)" in compiled.sql
    assert "ORDER BY" in compiled.sql
    assert "DESC" in compiled.sql
    assert compiled.sql.endswith("LIMIT 25")


def test_compiler_executes_controlled_calculated_fields_and_metrics() -> None:
    dataset = DatasetDefinition.model_validate(
        {
            "id": "sales",
            "name": "Sales",
            "data_source_id": "source-1",
            "query": {
                "kind": "sql",
                "sql": "SELECT month, amount, cost FROM sales",
            },
            "fields": (
                {"name": "month", "data_type": "string"},
                {"name": "amount", "data_type": "number"},
                {"name": "cost", "data_type": "number"},
            ),
            "semantics": {
                "calculated_fields": (
                    {
                        "name": "profit",
                        "label": "利润",
                        "data_type": "number",
                        "expression": {
                            "left_field": "amount",
                            "operator": "subtract",
                            "right_field": "cost",
                        },
                    },
                ),
                "metrics": (
                    {
                        "name": "total_profit",
                        "label": "利润合计",
                        "source_field": "profit",
                        "aggregation": "sum",
                    },
                ),
            },
        }
    )
    spec = ChartSpec(
        dataset_id="sales",
        dimensions=("month",),
        measures=(Measure(field="total_profit", aggregation=Aggregation.SUM),),
        filters=(
            Filter(
                field="profit",
                operator=FilterOperator.GREATER_THAN,
                value=LiteralValue(value=0),
            ),
        ),
        sort=(Sort(field="total_profit", direction=SortDirection.DESCENDING),),
        visual=VisualSpec(type=ChartType.LINE),
    )

    compiled = ChartQueryCompiler().compile(spec, dataset, {})

    assert "SUM(dataset_source.amount - dataset_source.cost) AS total_profit" in compiled.sql
    assert "dataset_source.amount - dataset_source.cost > :chart_filter_0" in compiled.sql
    assert "ORDER BY SUM(dataset_source.amount - dataset_source.cost) DESC" in compiled.sql
    assert compiled.parameters["chart_filter_0"] == 0


def test_compiler_switches_time_grain_from_a_validated_parameter() -> None:
    dataset = DatasetDefinition(
        id="events",
        name="Events",
        data_source_id="source-1",
        query=SqlQuery(sql="SELECT happened_at, amount FROM events"),
        fields=(
            DatasetField(name="happened_at", data_type=DataType.DATETIME),
            DatasetField(name="amount", data_type=DataType.NUMBER),
        ),
    )
    spec = ChartSpec.model_validate(
        {
            "dataset_id": "events",
            "dimensions": ["happened_at"],
            "measures": [{"field": "amount", "aggregation": "sum"}],
            "time_buckets": [{"field": "happened_at", "parameter": "time_grain"}],
            "visual": {"type": "line"},
        }
    )

    compiled = ChartQueryCompiler().compile(
        spec=spec,
        dataset=dataset,
        parameters={"time_grain": "month"},
        dialect="postgresql",
    )

    assert "DATE_TRUNC('MONTH', dataset_source.happened_at)" in compiled.sql
    assert "AS happened_at" in compiled.sql
    assert "GROUP BY DATE_TRUNC('MONTH', dataset_source.happened_at)" in compiled.sql

    with pytest.raises(ChartQueryInvalid) as captured:
        ChartQueryCompiler().compile(
            spec=spec,
            dataset=dataset,
            parameters={"time_grain": "decade"},
            dialect="postgresql",
        )
    assert captured.value.code == "CHART_TIME_GRAIN_INVALID"


def test_compiler_applies_parameter_driven_drilldown_without_cross_dataset_join() -> None:
    dataset = DatasetDefinition(
        id="sales",
        name="Sales",
        data_source_id="source-1",
        query=SqlQuery(sql="SELECT region, city, amount FROM sales"),
        fields=(
            DatasetField(name="region", data_type=DataType.STRING),
            DatasetField(name="city", data_type=DataType.STRING),
            DatasetField(name="amount", data_type=DataType.NUMBER),
        ),
    )
    spec = ChartSpec.model_validate(
        {
            "dataset_id": "sales",
            "dimensions": ["region"],
            "measures": [{"field": "amount", "aggregation": "sum"}],
            "drill_down": {
                "level_parameter": "geo_level",
                "levels": [
                    {"field": "region", "selection_parameter": "selected_region"},
                    {"field": "city", "selection_parameter": "selected_city"},
                ],
            },
            "visual": {"type": "bar"},
        }
    )

    compiled = ChartQueryCompiler().compile(
        spec=spec,
        dataset=dataset,
        parameters={"geo_level": 1, "selected_region": "east", "selected_city": None},
    )

    assert "dataset_source.city" in compiled.sql
    assert "GROUP BY dataset_source.city" in compiled.sql
    assert "dataset_source.region = :chart_filter_0" in compiled.sql
    assert compiled.parameters["chart_filter_0"] == "east"
    assert " JOIN " not in compiled.sql.upper()


@pytest.mark.parametrize(
    ("spec", "parameters", "code"),
    [
        (
            line_spec().model_copy(update={"dimensions": ("missing",)}),
            {},
            "CHART_FIELD_UNKNOWN",
        ),
        (
            line_spec(
                filters=(
                    Filter(
                        field="region",
                        operator=FilterOperator.EQUALS,
                        value=ParameterRef(name="missing"),
                    ),
                )
            ),
            {},
            "CHART_PARAMETER_MISSING",
        ),
        (
            line_spec().model_copy(update={"dataset_id": "other"}),
            {},
            "CHART_DATASET_MISMATCH",
        ),
        (
            line_spec().model_copy(update={"dimensions": ()}),
            {},
            "CHART_VISUAL_INVALID",
        ),
        (
            line_spec(
                filters=(
                    Filter(
                        field="region",
                        operator=FilterOperator.IN,
                        value=LiteralValue(value="east"),
                    ),
                )
            ),
            {},
            "CHART_FILTER_VALUE_INVALID",
        ),
    ],
)
def test_compiler_rejects_invalid_specs(
    spec: ChartSpec,
    parameters: dict[str, object],
    code: str,
) -> None:
    with pytest.raises(ChartQueryInvalid) as captured:
        ChartQueryCompiler().compile(
            spec=spec,
            dataset=sql_dataset(),
            parameters=parameters,
        )

    assert captured.value.code == code
