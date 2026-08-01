import pytest
from pydantic import ValidationError

from datapulse.contracts.ai import AiAnalysisRequest, AiAnalysisResponse, AnalysisPlan


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


def analysis_request_payload() -> dict[str, object]:
    return {
        "question": "分析最近几个月的销售趋势",
        "dataset_ids": ("sales",),
        "mode": "analysis",
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


def test_ai_analysis_request_requires_non_blank_question() -> None:
    payload = analysis_request_payload()
    payload["question"] = "   "

    with pytest.raises(ValidationError):
        AiAnalysisRequest.model_validate(payload)


def test_ai_analysis_request_requires_at_least_one_dataset() -> None:
    payload = analysis_request_payload()
    payload["dataset_ids"] = ()

    with pytest.raises(ValidationError):
        AiAnalysisRequest.model_validate(payload)


def test_ai_analysis_response_accepts_structured_plan_and_optional_chart() -> None:
    response = AiAnalysisResponse.model_validate(
        {
            "plan": analysis_payload(),
            "narrative": "最近几个月销售额总体上升。",
            "chart_spec": {
                "dataset_id": "sales",
                "dimensions": ("month",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
                "visual": {"type": "line"},
            },
            "warnings": ("样例数据已截断。",),
        }
    )

    assert response.plan.question == "按月份汇总销售额"
    assert response.chart_spec is not None
    assert response.chart_spec.visual.type == "line"
