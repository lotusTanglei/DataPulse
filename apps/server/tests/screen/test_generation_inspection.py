from datapulse.contracts.dashboard import Frame
from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.screen.compiler import DocumentCompiler
from datapulse.screen.inspection import ExecutionOutcome, GenerationInspector


def dataset() -> DatasetDefinition:
    return DatasetDefinition.model_validate(
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


def plan(*, dimension: str = "month", duplicate: bool = False) -> DashboardPlan:
    widgets: list[dict[str, object]] = [
        {
            "id": "trend",
            "title": "销售趋势",
            "intent": "展示销售趋势",
            "region_id": "main",
            "dataset_id": "sales",
            "chart_type": "line",
            "dimensions": (dimension,),
            "measures": ({"field": "amount", "aggregation": "sum"},),
            "filters": (
                {
                    "field": "region",
                    "operator": "equals",
                    "value": {"kind": "literal", "value": "华东"},
                },
            ),
        },
        {
            "id": "total",
            "title": "销售额",
            "intent": "展示销售额",
            "region_id": "summary",
            "dataset_id": "sales",
            "chart_type": "kpi",
            "measures": ({"field": "amount", "aggregation": "sum"},),
        },
    ]
    if duplicate:
        widgets.append({**widgets[0], "id": "trend-copy"})
    return DashboardPlan.model_validate(
        {
            "title": "销售总览",
            "audience": "销售负责人",
            "narrative": "销售指标与趋势。",
            "dataset_ids": ("sales",),
            "regions": (
                {"id": "summary", "kind": "summary", "order": 0},
                {"id": "main", "kind": "main", "order": 1},
            ),
            "widgets": tuple(widgets),
        }
    )


def compile_plan(value: DashboardPlan):
    return DocumentCompiler().compile(
        value,
        datasets={"sales": dataset()},
        authorized_dataset_ids={"sales"},
    )


def test_inspector_reports_fields_aggregations_filters_and_actual_rows() -> None:
    value = plan()
    document = compile_plan(value)

    result = GenerationInspector().inspect(
        value,
        document,
        datasets={"sales": dataset()},
        executions={
            "trend": ExecutionOutcome(status="ok", row_count=12),
            "total": ExecutionOutcome(status="ok", row_count=1),
        },
    )

    assert result.report.model_dump(mode="json") == {
        "valid": True,
        "widget_count": 2,
        "executed_count": 2,
        "fallback_count": 0,
        "checks": [
            {
                "widget_id": "trend",
                "dataset_id": "sales",
                "fields": ["month", "amount", "region"],
                "aggregations": ["amount:sum"],
                "filters": ["region:equals"],
                "row_count": 12,
                "status": "ok",
                "issues": [],
            },
            {
                "widget_id": "total",
                "dataset_id": "sales",
                "fields": ["amount"],
                "aggregations": ["amount:sum"],
                "filters": [],
                "row_count": 1,
                "status": "ok",
                "issues": [],
            },
        ],
        "issues": [],
    }
    assert result.document == document
    assert result.warnings == ()


def test_empty_and_failed_charts_become_editable_placeholders_with_warnings() -> None:
    value = plan()
    document = compile_plan(value)

    result = GenerationInspector().inspect(
        value,
        document,
        datasets={"sales": dataset()},
        executions={
            "trend": ExecutionOutcome(status="empty", row_count=0),
            "total": ExecutionOutcome(status="error", row_count=0, error_code="AI_CHART_INVALID"),
        },
    )

    placeholders = {component.id: component for component in result.document.components[1:]}
    assert placeholders["trend"].type == "builtin.panel"
    assert placeholders["trend"].data_binding == {}
    assert placeholders["total"].type == "builtin.panel"
    assert result.report.fallback_count == 2
    assert {check.status for check in result.report.checks} == {"empty", "error"}
    assert any("trend" in warning for warning in result.warnings)
    assert any("total" in warning for warning in result.warnings)


def test_semantic_checker_flags_non_temporal_trend_and_duplicate_charts() -> None:
    value = plan(dimension="region", duplicate=True)
    document = compile_plan(value)

    result = GenerationInspector().inspect(
        value,
        document,
        datasets={"sales": dataset()},
        executions={
            widget.id: ExecutionOutcome(status="ok", row_count=3) for widget in value.widgets
        },
    )

    codes = {issue.code for issue in result.report.issues}
    assert "SEMANTIC_TEMPORAL_EXPECTED" in codes
    assert "SEMANTIC_DUPLICATE_CHART" in codes


def test_semantic_checker_requires_category_dimensions_for_share_charts() -> None:
    payload = plan().model_dump(mode="json")
    payload["widgets"][0]["chart_type"] = "pie"
    value = DashboardPlan.model_validate(payload)
    document = compile_plan(value)

    result = GenerationInspector().inspect(
        value,
        document,
        datasets={"sales": dataset()},
        executions={
            widget.id: ExecutionOutcome(status="ok", row_count=3) for widget in value.widgets
        },
    )

    assert "SEMANTIC_CATEGORY_EXPECTED" in {issue.code for issue in result.report.issues}


def test_semantic_checker_flags_role_inversion_and_meaningless_aggregation() -> None:
    role_dataset = DatasetDefinition.model_validate(
        {
            **dataset().model_dump(mode="json"),
            "profile_overrides": (
                {"name": "region", "role": "measure"},
                {"name": "amount", "role": "identifier"},
            ),
        }
    )
    payload = plan(dimension="region").model_dump(mode="json")
    value = DashboardPlan.model_validate(payload)
    document = DocumentCompiler().compile(
        value,
        datasets={"sales": role_dataset},
        authorized_dataset_ids={"sales"},
    )

    result = GenerationInspector().inspect(
        value,
        document,
        datasets={"sales": role_dataset},
        executions={
            widget.id: ExecutionOutcome(status="ok", row_count=3) for widget in value.widgets
        },
    )

    codes = {issue.code for issue in result.report.issues}
    assert "SEMANTIC_DIMENSION_MEASURE_INVERTED" in codes
    assert "SEMANTIC_AGGREGATION_MEANINGLESS" in codes


def test_visual_checker_flags_overlap_overflow_minimum_size_contrast_and_density() -> None:
    value = plan()
    document = compile_plan(value)
    components = list(document.components)
    components[1] = components[1].model_copy(
        update={
            "frame": Frame(x=-1, y=100, width=40, height=30),
            "style": {"background": "#111111", "color": "#121212"},
        }
    )
    components[2] = components[2].model_copy(
        update={"frame": Frame(x=0, y=100, width=1910, height=970)}
    )
    invalid = document.model_copy(update={"components": tuple(components)})

    result = GenerationInspector().inspect(
        value,
        invalid,
        datasets={"sales": dataset()},
        executions={
            "trend": ExecutionOutcome(status="ok", row_count=2),
            "total": ExecutionOutcome(status="ok", row_count=1),
        },
    )

    codes = {issue.code for issue in result.report.issues}
    assert {
        "VISUAL_OUT_OF_BOUNDS",
        "VISUAL_TOO_SMALL",
        "VISUAL_OVERLAP",
        "VISUAL_CONTRAST_LOW",
        "VISUAL_DENSITY_HIGH",
    } <= codes


def test_cross_source_time_and_dimension_grain_mismatches_are_actionable_warnings() -> None:
    source_datasets = {
        "warehouse": DatasetDefinition.model_validate(
            {
                "id": "warehouse",
                "name": "主库月度数据",
                "data_source_id": "warehouse-source",
                "query": {"kind": "sql", "sql": "SELECT month, province, amount FROM sales"},
                "fields": (
                    {"name": "month", "data_type": "date"},
                    {"name": "province", "data_type": "string"},
                    {"name": "amount", "data_type": "number"},
                ),
            }
        ),
        "excel": DatasetDefinition.model_validate(
            {
                "id": "excel",
                "name": "Excel 日目标",
                "query": {"kind": "file", "asset_id": "target.xlsx", "format": "excel"},
                "fields": (
                    {"name": "day", "data_type": "date"},
                    {"name": "city", "data_type": "string"},
                    {"name": "amount", "data_type": "number"},
                ),
            }
        ),
    }
    source_plan = DashboardPlan.model_validate(
        {
            "title": "跨源趋势",
            "audience": "经营负责人",
            "narrative": "对照主库与 Excel。",
            "dataset_ids": tuple(source_datasets),
            "regions": ({"id": "main", "kind": "main"},),
            "widgets": (
                {
                    "id": "warehouse-trend",
                    "title": "月度销售",
                    "intent": "展示月度销售",
                    "region_id": "main",
                    "dataset_id": "warehouse",
                    "chart_type": "line",
                    "dimensions": ("month", "province"),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                },
                {
                    "id": "excel-trend",
                    "title": "每日目标",
                    "intent": "展示每日目标",
                    "region_id": "main",
                    "dataset_id": "excel",
                    "chart_type": "line",
                    "dimensions": ("day", "city"),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                },
            ),
        }
    )
    document = DocumentCompiler().compile(
        source_plan,
        datasets=source_datasets,
        authorized_dataset_ids=set(source_datasets),
    )

    result = GenerationInspector().inspect(
        source_plan,
        document,
        datasets=source_datasets,
        executions={
            widget.id: ExecutionOutcome(status="ok", row_count=3) for widget in source_plan.widgets
        },
    )

    assert any("时间粒度" in warning for warning in result.warnings)
    assert any("维度粒度" in warning for warning in result.warnings)
    assert all("源库视图或上游接口" in warning for warning in result.warnings)
