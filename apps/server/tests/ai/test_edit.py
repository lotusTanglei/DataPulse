import pytest

from datapulse.ai.edit import apply_ai_edit_commands, validate_edit_document
from datapulse.ai.models import AiAnalysisError
from datapulse.contracts.ai import (
    AiSetComponentStateCommand,
    AiUpdateDataBindingCommand,
    AiUpdateFrameCommand,
    AiUpdatePropsCommand,
)
from datapulse.contracts.dashboard import DashboardDocument
from tests.ai.test_service import sql_dataset_response


def document(*, locked: bool = False, with_chart: bool = False) -> DashboardDocument:
    return DashboardDocument.model_validate(
        {
            "canvas": {"width": 1920, "height": 1080, "background": {}},
            "theme": {"id": "datapulse-dark", "tokens": {}},
            "refresh": {"mode": "disabled"},
            "parameters": [],
            "components": [
                {
                    "id": "title",
                    "type": "builtin.text",
                    "frame": {"x": 40, "y": 40, "width": 600, "height": 80},
                    "state": {"locked": locked, "hidden": False},
                    "props": {"text": "旧标题", "font_size": 24},
                    "style": {},
                    "data_binding": {},
                    "interactions": [],
                },
                {
                    "id": "trend",
                    "type": "builtin.line",
                    "frame": {"x": 40, "y": 160, "width": 640, "height": 360},
                    "state": {"locked": False, "hidden": False},
                    "props": {"empty_text": "暂无数据"},
                    "style": {},
                    "data_binding": (
                        {
                            "chart_spec": {
                                "dataset_id": "sales",
                                "dimensions": ["month"],
                                "measures": [{"field": "amount", "aggregation": "sum"}],
                                "filters": [],
                                "sort": [],
                                "limit": 1000,
                                "visual": {"type": "line", "title": "销售趋势"},
                            }
                        }
                        if with_chart
                        else {}
                    ),
                    "interactions": [],
                },
            ],
        }
    )


def test_ai_edit_applies_multiple_changes_as_one_document_transform() -> None:
    updated = apply_ai_edit_commands(
        document(),
        (
            AiUpdatePropsCommand(component_id="title", patch={"text": "华东销售分析"}),
            AiUpdateFrameCommand(component_ids=("title",), patch={"x": 80, "y": 60}),
        ),
    )

    title = updated.components[0]
    assert title.props["text"] == "华东销售分析"
    assert title.frame.x == 80
    assert title.frame.y == 60


def test_ai_edit_rejects_locked_components_and_out_of_bounds_frames() -> None:
    with pytest.raises(AiAnalysisError, match="locked"):
        apply_ai_edit_commands(
            document(locked=True),
            (AiUpdatePropsCommand(component_id="title", patch={"text": "新标题"}),),
        )

    with pytest.raises(AiAnalysisError, match="outside"):
        apply_ai_edit_commands(
            document(),
            (AiUpdateFrameCommand(component_ids=("title",), patch={"x": 1500}),),
        )


def test_ai_edit_rejects_unknown_properties_and_invalid_bindings() -> None:
    with pytest.raises(AiAnalysisError):
        apply_ai_edit_commands(
            document(),
            (AiUpdatePropsCommand(component_id="title", patch={"script": "alert(1)"}),),
        )

    invalid_binding = AiUpdateDataBindingCommand(
        component_id="trend",
        data_binding={
            "chart_spec": {
                "dataset_id": "sales",
                "dimensions": ["unknown"],
                "measures": [{"field": "amount", "aggregation": "sum"}],
                "visual": {"type": "line"},
            }
        },
    )
    updated = apply_ai_edit_commands(document(), (invalid_binding,))
    with pytest.raises(AiAnalysisError):
        validate_edit_document(updated, {"sales": sql_dataset_response()})


def test_ai_edit_validates_existing_chart_binding_against_dataset_fields() -> None:
    validated = validate_edit_document(
        document(with_chart=True),
        {"sales": sql_dataset_response()},
    )

    assert validated.components[1].data_binding["chart_spec"]["dataset_id"] == "sales"


def test_ai_state_commands_cannot_bypass_component_locking() -> None:
    with pytest.raises(AiAnalysisError):
        apply_ai_edit_commands(
            document(locked=True),
            (
                AiSetComponentStateCommand(
                    component_ids=("title",),
                    patch={"locked": False},
                ),
            ),
        )
