import pytest
from pydantic import ValidationError

from datapulse.contracts.dashboard import DashboardDocument


def component(component_id: str = "sales-trend") -> dict[str, object]:
    return {
        "id": component_id,
        "type": "builtin.line",
        "frame": {
            "x": 100,
            "y": 80,
            "width": 600,
            "height": 360,
            "z_index": 3,
        },
        "state": {"locked": False, "hidden": False},
        "data_binding": {"chart_spec": {"dataset_id": "sales"}},
        "props": {"title": "月度销售趋势"},
        "style": {},
        "interactions": [
            {
                "event": "click",
                "action": "set_parameter",
                "parameter": "region",
                "field": "region",
            }
        ],
    }


def document_payload() -> dict[str, object]:
    return {
        "canvas": {
            "width": 1920,
            "height": 1080,
            "background": {"color": "#0b1020"},
        },
        "theme": {
            "id": "datapulse-dark",
            "tokens": {"text_primary": "#f8fafc"},
        },
        "refresh": {"mode": "interval", "interval_seconds": 30},
        "parameters": [
            {
                "id": "region",
                "name": "region",
                "data_type": "string",
                "default": "east",
                "mutable": True,
                "allowed_values": ["east", "west"],
            }
        ],
        "components": [component()],
    }


def test_dashboard_document_accepts_phase_two_shape() -> None:
    document = DashboardDocument.model_validate(document_payload())

    restored = DashboardDocument.model_validate_json(document.model_dump_json())

    assert restored == document
    assert document.schema_version == 1
    assert document.refresh.interval_seconds == 30
    assert document.components[0].frame.z_index == 3
    assert document.components[0].interactions[0].parameter == "region"


@pytest.mark.parametrize(
    "refresh",
    [
        {"mode": "interval", "interval_seconds": 15},
        {"mode": "interval", "interval_seconds": None},
        {"mode": "disabled", "interval_seconds": 30},
    ],
)
def test_dashboard_document_rejects_unsupported_refresh_policy(
    refresh: dict[str, object],
) -> None:
    payload = document_payload()
    payload["refresh"] = refresh

    with pytest.raises(ValidationError):
        DashboardDocument.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("width", 0), ("height", -1)],
)
def test_dashboard_document_rejects_non_positive_canvas_dimensions(
    field: str,
    value: int,
) -> None:
    payload = document_payload()
    canvas = dict(payload["canvas"])
    canvas[field] = value
    payload["canvas"] = canvas

    with pytest.raises(ValidationError):
        DashboardDocument.model_validate(payload)


def test_dashboard_document_rejects_rotation_and_nested_components() -> None:
    payload = document_payload()
    invalid = component()
    invalid["frame"] = {**invalid["frame"], "rotation": 15}
    invalid["children"] = []
    payload["components"] = [invalid]

    with pytest.raises(ValidationError):
        DashboardDocument.model_validate(payload)


def test_dashboard_document_rejects_duplicate_component_ids() -> None:
    payload = document_payload()
    payload["components"] = [component(), component()]

    with pytest.raises(ValidationError, match="component IDs must be unique"):
        DashboardDocument.model_validate(payload)


def test_dashboard_document_rejects_duplicate_parameter_names() -> None:
    payload = document_payload()
    payload["parameters"] = [
        payload["parameters"][0],
        {
            "id": "another-region",
            "name": "region",
            "data_type": "string",
        },
    ]

    with pytest.raises(ValidationError, match="parameter names must be unique"):
        DashboardDocument.model_validate(payload)


def test_dashboard_document_rejects_interaction_for_missing_parameter() -> None:
    payload = document_payload()
    payload["parameters"] = []

    with pytest.raises(ValidationError, match="unknown parameter"):
        DashboardDocument.model_validate(payload)
