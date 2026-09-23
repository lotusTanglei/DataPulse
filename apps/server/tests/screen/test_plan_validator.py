from copy import deepcopy

from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.screen.planning import PlanValidator


def dataset_payload() -> dict[str, object]:
    return {
        "id": "sales",
        "name": "销售数据",
        "query": {"kind": "sql", "sql": "SELECT month, region, amount FROM sales"},
        "fields": (
            {"name": "month", "data_type": "date"},
            {"name": "region", "data_type": "string"},
            {"name": "amount", "data_type": "number"},
        ),
    }


def plan_payload() -> dict[str, object]:
    return {
        "title": "销售总览",
        "audience": "销售负责人",
        "narrative": "先看指标，再看趋势。",
        "dataset_ids": ("sales",),
        "regions": (
            {"id": "summary", "kind": "summary"},
            {"id": "main", "kind": "main"},
        ),
        "widgets": (
            {
                "id": "trend",
                "title": "销售趋势",
                "intent": "展示销售额趋势",
                "region_id": "main",
                "dataset_id": "sales",
                "chart_type": "line",
                "dimensions": ("month",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
            },
        ),
    }


def validate(payload: dict[str, object], *, authorized: set[str] | None = None):
    plan = DashboardPlan.model_validate(payload)
    dataset = DatasetDefinition.model_validate(dataset_payload())
    return PlanValidator().validate(
        plan,
        datasets={"sales": dataset},
        authorized_dataset_ids=authorized if authorized is not None else {"sales"},
    )


def test_plan_validator_accepts_valid_fields_aggregation_shape_region_and_authorization() -> None:
    result = validate(plan_payload())

    assert result.valid is True
    assert result.issues == ()


def test_plan_validator_reports_unknown_field_with_widget_location() -> None:
    payload = deepcopy(plan_payload())
    payload["widgets"][0]["dimensions"] = ("missing",)  # type: ignore[index]

    result = validate(payload)

    assert result.valid is False
    assert result.issues[0].model_dump() == {
        "code": "PLAN_FIELD_UNKNOWN",
        "widget_id": "trend",
        "field": "dimensions[0]",
        "reason": "字段 missing 不存在于数据集 sales",
        "expected": "month, region, amount",
    }


def test_plan_validator_rejects_numeric_aggregation_on_text_field() -> None:
    payload = deepcopy(plan_payload())
    payload["widgets"][0]["measures"] = (  # type: ignore[index]
        {"field": "region", "aggregation": "sum"},
    )

    result = validate(payload)

    assert {issue.code for issue in result.issues} == {"PLAN_AGGREGATION_INVALID"}


def test_plan_validator_rejects_chart_shape_without_required_dimension() -> None:
    payload = deepcopy(plan_payload())
    payload["widgets"][0]["dimensions"] = ()  # type: ignore[index]

    result = validate(payload)

    assert {issue.code for issue in result.issues} == {"PLAN_SHAPE_INVALID"}


def test_plan_validator_rejects_partition_capacity_overflow() -> None:
    payload = deepcopy(plan_payload())
    widget = payload["widgets"][0]  # type: ignore[index]
    payload["widgets"] = tuple(
        {**widget, "id": f"trend-{index}"} for index in range(17)  # type: ignore[arg-type]
    )

    result = validate(payload)

    assert {issue.code for issue in result.issues} == {"PLAN_REGION_DENSITY_INVALID"}


def test_plan_validator_rejects_missing_or_unauthorized_dataset() -> None:
    result = validate(plan_payload(), authorized=set())

    assert result.valid is False
    assert result.issues[0].code == "PLAN_DATASET_UNAUTHORIZED"
    assert result.issues[0].widget_id == "trend"


def test_plan_validator_locates_unknown_widget_dataset_separately_from_authorization() -> None:
    payload = deepcopy(plan_payload())
    payload["dataset_ids"] = ("missing",)
    payload["widgets"][0]["dataset_id"] = "missing"  # type: ignore[index]

    result = validate(payload, authorized={"missing"})

    assert result.valid is False
    assert result.issues[0].model_dump() == {
        "code": "PLAN_DATASET_UNKNOWN",
        "widget_id": "trend",
        "field": "dataset_id",
        "reason": "数据集 missing 不存在",
        "expected": "已登记的数据集",
    }
