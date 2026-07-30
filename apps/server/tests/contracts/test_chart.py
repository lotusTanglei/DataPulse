import pytest
from pydantic import ValidationError

from datapulse.contracts.chart import ChartSpec


def chart_payload() -> dict[str, object]:
    return {
        "dataset_id": "sales",
        "dimensions": ("month",),
        "measures": ({"field": "amount", "aggregation": "sum"},),
        "filters": (
            {
                "field": "region",
                "operator": "equals",
                "value": {"kind": "parameter", "name": "region"},
            },
            {
                "field": "amount",
                "operator": "greater_than",
                "value": {"kind": "literal", "value": 0},
            },
        ),
        "sort": ({"field": "month", "direction": "asc"},),
        "limit": 1000,
        "visual": {"type": "line", "title": "月度销售趋势"},
    }


def test_chart_spec_round_trips_parameter_and_literal_filters() -> None:
    chart = ChartSpec.model_validate(chart_payload())

    restored = ChartSpec.model_validate_json(chart.model_dump_json())

    assert restored == chart
    assert chart.schema_version == 1
    assert chart.filters[0].value.kind == "parameter"
    assert chart.filters[1].value.kind == "literal"
    assert chart.measures[0].aggregation == "sum"


@pytest.mark.parametrize("aggregation", ["none", "count_distinct", "median"])
def test_chart_spec_rejects_unsupported_aggregations(aggregation: str) -> None:
    payload = chart_payload()
    payload["measures"] = ({"field": "amount", "aggregation": aggregation},)

    with pytest.raises(ValidationError):
        ChartSpec.model_validate(payload)


@pytest.mark.parametrize("limit", [0, 5001])
def test_chart_spec_rejects_limits_outside_supported_range(limit: int) -> None:
    payload = chart_payload()
    payload["limit"] = limit

    with pytest.raises(ValidationError):
        ChartSpec.model_validate(payload)


def test_chart_spec_rejects_untyped_filter_value() -> None:
    payload = chart_payload()
    payload["filters"] = ({"field": "region", "operator": "equals", "value": "east"},)

    with pytest.raises(ValidationError):
        ChartSpec.model_validate(payload)
