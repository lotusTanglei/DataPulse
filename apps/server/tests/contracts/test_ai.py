import pytest
from pydantic import ValidationError

from datapulse.contracts.ai import AnalysisPlan


def analysis_payload() -> dict[str, object]:
    return {
        "question": "按月份汇总销售额",
        "dataset_ids": ("sales",),
        "dimensions": ("month",),
        "measures": ({"field": "amount", "aggregation": "sum"},),
        "filters": (),
        "sort": ({"field": "month", "direction": "asc"},),
        "recommended_chart": "line",
        "assumptions": (),
        "requires_confirmation": True,
    }


def test_analysis_plan_round_trips_with_schema_version() -> None:
    plan = AnalysisPlan.model_validate(analysis_payload())

    restored = AnalysisPlan.model_validate_json(plan.model_dump_json())

    assert plan.schema_version == 1
    assert restored == plan
    assert restored.question == "按月份汇总销售额"


def test_analysis_plan_requires_at_least_one_dataset() -> None:
    payload = analysis_payload()
    payload["dataset_ids"] = ()

    with pytest.raises(ValidationError):
        AnalysisPlan.model_validate(payload)
