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
