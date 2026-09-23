import json
from pathlib import Path

import pytest

from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.screen.compiler import DocumentCompiler
from datapulse.screen.planning import PlanValidationError
from datapulse.screen.templates import TEMPLATE_SKELETONS

SNAPSHOT = Path(__file__).with_name("snapshots") / "document_compiler.json"


def datasets() -> dict[str, DatasetDefinition]:
    return {
        "sales": DatasetDefinition.model_validate(
            {
                "id": "sales",
                "name": "销售数据",
                "query": {"kind": "sql", "sql": "SELECT month, region, amount FROM sales"},
                "fields": (
                    {"name": "month", "data_type": "date"},
                    {"name": "region", "data_type": "string"},
                    {"name": "amount", "data_type": "number"},
                ),
            }
        )
    }


def plan_payload() -> dict[str, object]:
    return {
        "title": "销售经营总览",
        "audience": "区域负责人",
        "narrative": "先看核心指标，再看趋势和区域贡献。",
        "dataset_ids": ("sales",),
        "layout": {
            "template": "executive-overview",
            "grid_columns": 24,
            "density": "comfortable",
            "theme": "dark",
        },
        "regions": (
            {"id": "summary", "kind": "summary", "title": "核心指标", "order": 0},
            {"id": "main", "kind": "main", "title": "经营趋势", "order": 1},
        ),
        "widgets": (
            {
                "id": "revenue",
                "title": "销售额",
                "intent": "展示销售额",
                "region_id": "summary",
                "dataset_id": "sales",
                "chart_type": "kpi",
                "measures": ({"field": "amount", "aggregation": "sum"},),
            },
            {
                "id": "trend",
                "title": "销售趋势",
                "intent": "展示月度销售额趋势",
                "region_id": "main",
                "dataset_id": "sales",
                "chart_type": "line",
                "dimensions": ("month",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
            },
            {
                "id": "ranking",
                "title": "区域排名",
                "intent": "比较各区域销售额",
                "region_id": "main",
                "dataset_id": "sales",
                "chart_type": "bar",
                "dimensions": ("region",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
            },
        ),
    }


def test_document_compiler_is_deterministic_and_matches_snapshot() -> None:
    plan = DashboardPlan.model_validate(plan_payload())
    compiler = DocumentCompiler()

    first = compiler.compile(plan, datasets=datasets(), authorized_dataset_ids={"sales"})
    second = compiler.compile(plan, datasets=datasets(), authorized_dataset_ids={"sales"})

    assert first == second
    actual = json.dumps(first.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    assert actual == SNAPSHOT.read_text(encoding="utf-8")
    assert all("chart_spec" in component.data_binding for component in first.components[1:])


def test_partition_density_allows_25_widgets_without_overlap() -> None:
    payload = plan_payload()
    payload["regions"] = tuple(
        {"id": f"region-{index}", "kind": "main", "order": index} for index in range(5)
    )
    base = payload["widgets"][1]  # type: ignore[index]
    payload["widgets"] = tuple(
        {
            **base,  # type: ignore[arg-type]
            "id": f"chart-{index}",
            "region_id": f"region-{index // 5}",
        }
        for index in range(25)
    )
    plan = DashboardPlan.model_validate(payload)

    document = DocumentCompiler().compile(
        plan,
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )

    assert len(document.components) == 26
    for index, first in enumerate(document.components):
        for second in document.components[index + 1 :]:
            assert not (
                first.frame.x < second.frame.x + second.frame.width
                and first.frame.x + first.frame.width > second.frame.x
                and first.frame.y < second.frame.y + second.frame.height
                and first.frame.y + first.frame.height > second.frame.y
            )


def test_five_templates_are_skeleton_slot_and_theme_token_definitions() -> None:
    assert set(TEMPLATE_SKELETONS) == {
        "executive-overview",
        "trend-focus",
        "comparison-board",
        "status-wall",
        "analysis-lab",
    }
    for skeleton in TEMPLATE_SKELETONS.values():
        assert skeleton.region_columns
        assert skeleton.region_slots
        assert skeleton.slot_gap > 0
        assert set(skeleton.theme_tokens) == {"dark", "light"}
        assert skeleton.theme_tokens["dark"]["font_family"]
        assert skeleton.theme_tokens["light"]["panel_background"]


@pytest.mark.parametrize("template", tuple(TEMPLATE_SKELETONS))
def test_template_skeleton_places_main_and_sidebar_in_distinct_slots(template: str) -> None:
    payload = plan_payload()
    payload["layout"] = {**payload["layout"], "template": template}  # type: ignore[arg-type]
    payload["regions"] = (
        {"id": "main", "kind": "main", "order": 0},
        {"id": "sidebar", "kind": "sidebar", "order": 1},
    )
    payload["widgets"] = tuple(
        {
            **widget,
            "region_id": "main" if index < 2 else "sidebar",
        }
        for index, widget in enumerate(payload["widgets"])  # type: ignore[union-attr]
    )

    document = DocumentCompiler().compile(
        DashboardPlan.model_validate(payload),
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )

    components = {component.id: component for component in document.components}
    main = components["revenue"].frame
    sidebar = components["ranking"].frame
    assert main.y == sidebar.y
    assert main.x + main.width < sidebar.x


def test_compiler_applies_visual_defaults_and_safe_margins() -> None:
    plan = DashboardPlan.model_validate(plan_payload())
    document = DocumentCompiler().compile(
        plan,
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )

    assert document.canvas.background == {"color": "#07111f"}
    assert document.theme.tokens["font_family"] == "Inter, system-ui, sans-serif"
    assert document.components[0].props["font_size"] == 32
    assert min(component.frame.x for component in document.components) >= 48
    assert min(component.frame.y for component in document.components) >= 32


def test_compiler_applies_light_theme_tokens() -> None:
    payload = plan_payload()
    payload["layout"] = {**payload["layout"], "theme": "light"}  # type: ignore[arg-type]
    plan = DashboardPlan.model_validate(payload)

    document = DocumentCompiler().compile(
        plan,
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )

    assert document.theme.id == "datapulse-light"
    assert document.canvas.background == {"color": "#f8fafc"}
    assert document.theme.tokens["panel_background"] == "#ffffff"
    assert document.theme.tokens["text_primary"] == "#0f172a"
    assert document.components[0].style["color"] == "#0f172a"


def test_compiler_groups_widgets_from_the_same_source_with_stable_order() -> None:
    source_datasets = {
        "sales": DatasetDefinition.model_validate(
            {
                "id": "sales",
                "name": "主库销售",
                "data_source_id": "warehouse",
                "query": {"kind": "sql", "sql": "SELECT amount FROM sales"},
                "fields": ({"name": "amount", "data_type": "number"},),
            }
        ),
        "profit": DatasetDefinition.model_validate(
            {
                "id": "profit",
                "name": "主库利润",
                "data_source_id": "warehouse",
                "query": {"kind": "sql", "sql": "SELECT amount FROM profit"},
                "fields": ({"name": "amount", "data_type": "number"},),
            }
        ),
        "targets": DatasetDefinition.model_validate(
            {
                "id": "targets",
                "name": "Excel 目标",
                "query": {"kind": "file", "asset_id": "targets.xlsx", "format": "excel"},
                "fields": ({"name": "amount", "data_type": "number"},),
            }
        ),
        "orders": DatasetDefinition.model_validate(
            {
                "id": "orders",
                "name": "接口订单",
                "data_source_id": "orders-api",
                "query": {"kind": "rest", "url": "https://api.example.com/orders"},
                "fields": ({"name": "amount", "data_type": "number"},),
            }
        ),
    }
    plan = DashboardPlan.model_validate(
        {
            "title": "多源经营总览",
            "audience": "经营负责人",
            "narrative": "按来源组织核心指标。",
            "dataset_ids": tuple(source_datasets),
            "regions": ({"id": "summary", "kind": "summary"},),
            "widgets": tuple(
                {
                    "id": widget_id,
                    "title": widget_id,
                    "intent": "展示指标",
                    "region_id": "summary",
                    "dataset_id": dataset_id,
                    "chart_type": "kpi",
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                }
                for widget_id, dataset_id in (
                    ("sales-total", "sales"),
                    ("target-total", "targets"),
                    ("profit-total", "profit"),
                    ("order-total", "orders"),
                )
            ),
        }
    )

    document = DocumentCompiler().compile(
        plan,
        datasets=source_datasets,
        authorized_dataset_ids=set(source_datasets),
    )

    assert [component.id for component in document.components[1:]] == [
        "sales-total",
        "profit-total",
        "target-total",
        "order-total",
    ]


def test_recompile_regions_only_replaces_components_in_affected_region() -> None:
    previous_plan = DashboardPlan.model_validate(plan_payload())
    compiler = DocumentCompiler()
    previous_document = compiler.compile(
        previous_plan,
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )
    payload = plan_payload()
    payload["widgets"] = tuple(
        {
            **widget,
            **({"chart_type": "area", "title": "销售额趋势"} if widget["id"] == "trend" else {}),
        }
        for widget in payload["widgets"]  # type: ignore[union-attr]
    )
    next_plan = DashboardPlan.model_validate(payload)

    document = compiler.recompile_regions(
        previous_plan=previous_plan,
        plan=next_plan,
        document=previous_document,
        affected_region_ids={"main"},
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )

    previous_by_id = {component.id: component for component in previous_document.components}
    next_by_id = {component.id: component for component in document.components}
    assert next_by_id["plan-title"] == previous_by_id["plan-title"]
    assert next_by_id["revenue"] == previous_by_id["revenue"]
    assert next_by_id["trend"] != previous_by_id["trend"]
    assert next_by_id["trend"].type == "builtin.line"
    assert next_by_id["trend"].data_binding["chart_spec"]["visual"]["type"] == "area"


def test_recompile_regions_keeps_other_regions_fixed_when_widget_count_changes() -> None:
    previous_plan = DashboardPlan.model_validate(plan_payload())
    compiler = DocumentCompiler()
    previous_document = compiler.compile(
        previous_plan,
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )
    payload = plan_payload()
    payload["widgets"] = (
        *payload["widgets"],  # type: ignore[union-attr]
        {
            "id": "detail",
            "title": "区域明细",
            "intent": "展示区域销售明细",
            "region_id": "main",
            "dataset_id": "sales",
            "chart_type": "table",
            "dimensions": ("region",),
            "measures": ({"field": "amount", "aggregation": "sum"},),
        },
    )
    next_plan = DashboardPlan.model_validate(payload)

    document = compiler.recompile_regions(
        previous_plan=previous_plan,
        plan=next_plan,
        document=previous_document,
        affected_region_ids={"main"},
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )

    previous_by_id = {component.id: component for component in previous_document.components}
    next_by_id = {component.id: component for component in document.components}
    assert next_by_id["revenue"] == previous_by_id["revenue"]
    assert next_by_id["plan-title"] == previous_by_id["plan-title"]
    assert {"trend", "ranking", "detail"} <= set(next_by_id)
    for component_id in ("trend", "ranking", "detail"):
        frame = next_by_id[component_id].frame
        assert frame.x >= 48
        assert frame.y >= previous_by_id["trend"].frame.y
        assert frame.x + frame.width <= 1872
        assert frame.y + frame.height <= 1048


def test_recompile_regions_rejects_changes_outside_declared_scope() -> None:
    previous_plan = DashboardPlan.model_validate(plan_payload())
    compiler = DocumentCompiler()
    previous_document = compiler.compile(
        previous_plan,
        datasets=datasets(),
        authorized_dataset_ids={"sales"},
    )
    payload = plan_payload()
    payload["widgets"] = tuple(
        {**widget, **({"title": "销售额（修订）"} if widget["id"] == "revenue" else {})}
        for widget in payload["widgets"]  # type: ignore[union-attr]
    )
    next_plan = DashboardPlan.model_validate(payload)

    with pytest.raises(PlanValidationError) as caught:
        compiler.recompile_regions(
            previous_plan=previous_plan,
            plan=next_plan,
            document=previous_document,
            affected_region_ids={"main"},
            datasets=datasets(),
            authorized_dataset_ids={"sales"},
        )

    assert caught.value.result.issues[0].code == "PLAN_RECOMPILE_SCOPE_INVALID"
