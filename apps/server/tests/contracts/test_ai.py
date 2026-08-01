import pytest
from pydantic import ValidationError

from datapulse.contracts.ai import (
    AiAnalysisRequest,
    AiAnalysisResponse,
    AiChartRequest,
    AiChartResponse,
    AiScreenRequest,
    AiScreenResponse,
    AnalysisPlan,
)


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


@pytest.mark.parametrize(
    "payload",
    [
        {
            "question": "分析趋势",
            "dataset_ids": tuple(f"dataset-{index}" for index in range(9)),
        },
        {
            "question": "x" * 4001,
            "dataset_ids": ("sales",),
        },
    ],
)
def test_ai_analysis_request_limits_prompt_resources(payload: dict[str, object]) -> None:
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
            "preview": {
                "request_id": "analysis-preview-1",
                "columns": (
                    {"name": "month", "data_type": "string"},
                    {"name": "amount", "data_type": "number"},
                ),
                "rows": (("2026-01", 120),),
                "row_count": 1,
                "truncated": False,
                "duration_ms": 4,
            },
            "warnings": ("样例数据已截断。",),
        }
    )

    assert response.plan.question == "按月份汇总销售额"
    assert response.chart_spec is not None
    assert response.chart_spec.visual.type == "line"
    assert response.preview.rows == (("2026-01", 120),)


def test_ai_chart_request_accepts_optional_target_component_type() -> None:
    request = AiChartRequest.model_validate(
        {
            "question": "按区域统计销售额",
            "dataset_id": "sales",
            "target_component_type": "bar",
        }
    )

    assert request.target_component_type == "bar"


def test_ai_chart_request_requires_non_blank_question() -> None:
    with pytest.raises(ValidationError):
        AiChartRequest.model_validate(
            {
                "question": "  ",
                "dataset_id": "sales",
            }
        )


def test_ai_chart_request_limits_question_length() -> None:
    with pytest.raises(ValidationError):
        AiChartRequest.model_validate(
            {
                "question": "x" * 4001,
                "dataset_id": "sales",
            }
        )


def test_ai_chart_response_round_trips_preview_payload() -> None:
    response = AiChartResponse.model_validate(
        {
            "chart_spec": {
                "dataset_id": "sales",
                "dimensions": ("region",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
                "visual": {"type": "bar"},
            },
            "explanation": "按区域汇总销售额，适合用柱状图比较各区域表现。",
            "preview": {
                "request_id": "preview-1",
                "columns": (
                    {"name": "region", "data_type": "string"},
                    {"name": "amount", "data_type": "number"},
                ),
                "rows": (("north", 120),),
                "row_count": 1,
                "truncated": False,
                "duration_ms": 4,
            },
            "warnings": ("预览结果已截断到 1 行。",),
        }
    )

    restored = AiChartResponse.model_validate_json(response.model_dump_json())

    assert restored == response
    assert response.chart_spec.visual.type == "bar"
    assert response.preview.rows == (("north", 120),)


def test_ai_screen_request_defaults_canvas_and_theme() -> None:
    request = AiScreenRequest.model_validate(
        {
            "question": "生成销售运营大屏",
            "dataset_ids": ("sales",),
        }
    )

    assert request.canvas_width == 1920
    assert request.canvas_height == 1080
    assert request.theme == "dark"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "question": "生成大屏",
            "dataset_ids": tuple(f"dataset-{index}" for index in range(9)),
        },
        {
            "question": "x" * 4001,
            "dataset_ids": ("sales",),
        },
        {
            "question": "生成大屏",
            "dataset_ids": ("sales",),
            "canvas_width": 7681,
        },
        {
            "question": "生成大屏",
            "dataset_ids": ("sales",),
            "canvas_height": 7681,
        },
    ],
)
def test_ai_screen_request_limits_prompt_resources(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AiScreenRequest.model_validate(payload)


def test_ai_screen_response_round_trips_dashboard_document() -> None:
    response = AiScreenResponse.model_validate(
        {
            "document": {
                "canvas": {"width": 1920, "height": 1080},
                "theme": {"id": "datapulse-dark", "tokens": {}},
                "refresh": {"mode": "disabled"},
                "parameters": (
                    {
                        "id": "region",
                        "name": "region",
                        "data_type": "string",
                        "default": "east",
                        "mutable": True,
                    },
                ),
                "components": (
                    {
                        "id": "title",
                        "type": "builtin.text",
                        "frame": {"x": 40, "y": 32, "width": 640, "height": 72},
                        "props": {"text": "销售运营大屏"},
                    },
                ),
            },
            "explanation": "大屏包含标题和筛选参数。",
            "warnings": (),
        }
    )

    restored = AiScreenResponse.model_validate_json(response.model_dump_json())

    assert restored == response
    assert response.document.theme.id == "datapulse-dark"
    assert response.document.components[0].type == "builtin.text"
