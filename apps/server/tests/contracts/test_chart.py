import pytest
from pydantic import ValidationError

from datapulse.contracts.chart import ChartSpec


def chart_payload() -> dict[str, object]:
    return {
        "dataset_id": "sales",
        "dimensions": ("month",),
        "measures": ({"field": "amount", "aggregation": "sum"},),
        "filters": (),
        "sort": ({"field": "month", "direction": "asc"},),
        "limit": 1000,
        "visual": {"type": "line", "title": "月度销售趋势"},
    }


def test_chart_spec_round_trips_with_schema_version() -> None:
    chart = ChartSpec.model_validate(chart_payload())

    restored = ChartSpec.model_validate_json(chart.model_dump_json())

    assert chart.schema_version == 1
    assert restored == chart
    assert restored.measures[0].aggregation == "sum"


@pytest.mark.parametrize("limit", [0, 5001])
def test_chart_spec_rejects_limits_outside_supported_range(limit: int) -> None:
    payload = chart_payload()
    payload["limit"] = limit

    with pytest.raises(ValidationError):
        ChartSpec.model_validate(payload)
