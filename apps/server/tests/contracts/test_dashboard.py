import pytest
from pydantic import ValidationError

from datapulse.contracts.dashboard import DashboardDocument


def component(component_id: str = "sales-trend") -> dict[str, object]:
    return {
        "id": component_id,
        "type": "echarts.line",
        "plugin": {"id": "builtin-echarts", "version": "1.0.0"},
        "geometry": {
            "x": 100,
            "y": 80,
            "width": 600,
            "height": 360,
            "rotation": 0,
            "z_index": 3,
        },
        "data_binding": {"dataset_id": "sales"},
        "properties": {"title": "月度销售趋势"},
        "style": {},
    }


def test_dashboard_document_round_trips_with_schema_version() -> None:
    document = DashboardDocument(
        canvas={"width": 1920, "height": 1080},
        components=(component(),),
    )

    restored = DashboardDocument.model_validate_json(document.model_dump_json())

    assert document.schema_version == 1
    assert restored == document
    assert restored.components[0].geometry.width == 600


@pytest.mark.parametrize(("field", "value"), [("width", 0), ("height", -1)])
def test_dashboard_document_rejects_non_positive_canvas_dimensions(field: str, value: int) -> None:
    canvas = {"width": 1920, "height": 1080}
    canvas[field] = value

    with pytest.raises(ValidationError):
        DashboardDocument(canvas=canvas)


def test_dashboard_document_rejects_duplicate_component_ids() -> None:
    duplicate = component()

    with pytest.raises(ValidationError, match="component IDs must be unique"):
        DashboardDocument(
            canvas={"width": 1920, "height": 1080},
            components=(duplicate, duplicate),
        )
