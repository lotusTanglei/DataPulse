import json

import pytest
from pydantic import ValidationError

from datapulse.contracts.dashboard_plan import DashboardPlan


def plan_payload() -> dict[str, object]:
    return {
        "title": "销售经营总览",
        "audience": "区域负责人",
        "narrative": "先看核心指标，再看趋势与区域贡献。",
        "dataset_ids": ("sales",),
        "layout": {
            "template": "executive-overview",
            "grid_columns": 24,
            "density": "comfortable",
        },
        "regions": (
            {"id": "summary", "kind": "summary", "title": "核心指标", "order": 0},
            {"id": "main", "kind": "main", "title": "经营趋势", "order": 1},
        ),
        "widgets": (
            {
                "id": "revenue-trend",
                "title": "销售额趋势",
                "intent": "展示月度销售额变化",
                "region_id": "main",
                "dataset_id": "sales",
                "chart_type": "line",
                "dimensions": ("month",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
            },
        ),
    }


def test_dashboard_plan_round_trips_without_pixel_coordinates() -> None:
    plan = DashboardPlan.model_validate(plan_payload())

    restored = DashboardPlan.model_validate_json(plan.model_dump_json())

    assert restored == plan
    assert plan.schema_version == 1
    assert plan.widgets[0].dataset_id == "sales"
    dumped = json.dumps(plan.model_dump(mode="json"), ensure_ascii=False)
    for forbidden in ('"frame"', '"x"', '"y"', '"width"', '"height"'):
        assert forbidden not in dumped


def test_dashboard_plan_widget_accepts_exactly_one_dataset_reference() -> None:
    payload = plan_payload()
    widget = dict(payload["widgets"][0])  # type: ignore[index]
    widget.pop("dataset_id")
    widget["dataset_ids"] = ("sales", "targets")
    payload["widgets"] = (widget,)

    with pytest.raises(ValidationError):
        DashboardPlan.model_validate(payload)


def test_dashboard_plan_rejects_unknown_region_and_dataset_references() -> None:
    for field, value in (("region_id", "missing"), ("dataset_id", "unauthorized")):
        payload = plan_payload()
        widget = dict(payload["widgets"][0])  # type: ignore[index]
        widget[field] = value
        payload["widgets"] = (widget,)

        with pytest.raises(ValidationError):
            DashboardPlan.model_validate(payload)


def test_dashboard_plan_rejects_duplicate_ids() -> None:
    payload = plan_payload()
    payload["widgets"] = (*payload["widgets"], payload["widgets"][0])  # type: ignore[index]

    with pytest.raises(ValidationError):
        DashboardPlan.model_validate(payload)


def test_dashboard_plan_carries_linkage_time_grain_and_drilldown_without_coordinates() -> None:
    payload = plan_payload()
    payload["parameters"] = (
        {
            "id": "region",
            "name": "region",
            "data_type": "string",
            "default": "east",
        },
        {
            "id": "time-grain",
            "name": "time_grain",
            "data_type": "string",
            "default": "month",
            "allowed_values": ["day", "week", "month", "quarter", "year"],
        },
        {"id": "geo-level", "name": "geo_level", "data_type": "integer", "default": 0},
        {
            "id": "selected-region",
            "name": "selected_region",
            "data_type": "string",
            "default": "east",
        },
        {
            "id": "selected-city",
            "name": "selected_city",
            "data_type": "string",
            "default": "",
        },
    )
    widget = dict(payload["widgets"][0])  # type: ignore[index]
    widget["dimensions"] = ("month", "region")
    widget["time_buckets"] = ({"field": "month", "parameter": "time_grain"},)
    widget["drill_down"] = {
        "level_parameter": "geo_level",
        "levels": (
            {"field": "region", "selection_parameter": "selected_region"},
            {"field": "city", "selection_parameter": "selected_city"},
        ),
    }
    widget["interactions"] = (
        {
            "event": "click",
            "action": "set_parameter",
            "parameter": "region",
            "field": "region",
        },
    )
    payload["widgets"] = (widget,)

    plan = DashboardPlan.model_validate(payload)

    assert plan.widgets[0].time_buckets[0].parameter == "time_grain"
    assert plan.widgets[0].drill_down.levels[1].field == "city"
    assert plan.widgets[0].interactions[0].parameter == "region"
    assert '"frame"' not in json.dumps(plan.model_dump(mode="json"))
