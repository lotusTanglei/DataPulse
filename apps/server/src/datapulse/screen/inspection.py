from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import Field

from datapulse.contracts.chart import Aggregation, ChartType
from datapulse.contracts.common import ContractModel
from datapulse.contracts.dashboard import ComponentInstance, DashboardDocument
from datapulse.contracts.dashboard_plan import DashboardPlan, PlanWidget
from datapulse.contracts.dataset import DatasetDefinition, DataType
from datapulse.contracts.generation import (
    GenerationIssue,
    GenerationSelfCheckReport,
    WidgetSelfCheck,
)
from datapulse.screen.sources import dataset_source_key


class ExecutionOutcome(ContractModel):
    status: Literal["ok", "empty", "error"]
    row_count: int = Field(ge=0)
    error_code: str | None = None


class GenerationInspectionResult(ContractModel):
    document: DashboardDocument
    report: GenerationSelfCheckReport
    warnings: tuple[str, ...] = Field(default_factory=tuple)


def _unique(items: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _semantic_issues(
    plan: DashboardPlan,
    datasets: Mapping[str, DatasetDefinition],
) -> tuple[GenerationIssue, ...]:
    issues: list[GenerationIssue] = []
    signatures: dict[tuple[object, ...], str] = {}
    for widget in plan.widgets:
        dataset = datasets[widget.dataset_id]
        types = {field.name: field.data_type for field in dataset.fields}
        roles = {
            override.name: override.role
            for override in dataset.profile_overrides
            if override.role is not None
        }
        if widget.chart_type in {ChartType.LINE, ChartType.AREA} and widget.dimensions:
            field = widget.dimensions[0]
            if types.get(field) not in {DataType.DATE, DataType.DATETIME}:
                issues.append(
                    GenerationIssue(
                        code="SEMANTIC_TEMPORAL_EXPECTED",
                        component_id=widget.id,
                        field="dimensions[0]",
                        message="趋势图的首个维度应为日期或日期时间字段",
                    )
                )

        if widget.chart_type is ChartType.PIE and widget.dimensions:
            field = widget.dimensions[0]
            role = roles.get(field)
            categorical_roles = {
                "boolean",
                "dimension",
                "geography",
                "identifier",
                "text",
            }
            if role not in categorical_roles and types.get(field) not in {
                DataType.BOOLEAN,
                DataType.STRING,
            }:
                issues.append(
                    GenerationIssue(
                        code="SEMANTIC_CATEGORY_EXPECTED",
                        component_id=widget.id,
                        field="dimensions[0]",
                        message="占比图的维度应为类别字段",
                    )
                )

        for index, field in enumerate(widget.dimensions):
            if roles.get(field) == "measure":
                issues.append(
                    GenerationIssue(
                        code="SEMANTIC_DIMENSION_MEASURE_INVERTED",
                        component_id=widget.id,
                        field=f"dimensions[{index}]",
                        message=f"字段 {field} 的画像角色为指标，不应作为维度",
                    )
                )

        for index, measure in enumerate(widget.measures):
            role = roles.get(measure.field)
            meaningless = (
                role == "identifier" and measure.aggregation is not Aggregation.COUNT
            ) or (
                role in {"boolean", "dimension", "geography", "text"}
                and measure.aggregation in {Aggregation.SUM, Aggregation.AVERAGE}
            )
            if meaningless:
                issues.append(
                    GenerationIssue(
                        code="SEMANTIC_AGGREGATION_MEANINGLESS",
                        component_id=widget.id,
                        field=f"measures[{index}].aggregation",
                        message=(
                            f"字段 {measure.field} 的画像角色为 {role}，"
                            f"不适合 {measure.aggregation.value} 聚合"
                        ),
                    )
                )

        signature = (
            widget.dataset_id,
            widget.chart_type,
            widget.dimensions,
            tuple((item.field, item.aggregation) for item in widget.measures),
            tuple((item.field, item.operator, repr(item.value)) for item in widget.filters),
        )
        duplicate_of = signatures.get(signature)
        if duplicate_of is not None:
            issues.append(
                GenerationIssue(
                    code="SEMANTIC_DUPLICATE_CHART",
                    component_id=widget.id,
                    field="widget",
                    message=f"图表与组件 {duplicate_of} 重复",
                )
            )
        else:
            signatures[signature] = widget.id
    return tuple(issues)


def _temporal_grain(field: str, data_type: DataType) -> str | None:
    if data_type not in {DataType.DATE, DataType.DATETIME}:
        return None
    normalized = field.lower()
    grains = (
        ("quarter", ("quarter", "季度")),
        ("month", ("month", "月份", "年月")),
        ("week", ("week", "周")),
        ("year", ("year", "年份", "年度")),
        ("day", ("day", "date", "日期")),
        ("hour", ("hour", "time", "timestamp", "小时", "时间")),
    )
    for grain, tokens in grains:
        if any(token in normalized for token in tokens):
            return grain
    return "hour" if data_type is DataType.DATETIME else "day"


def _dimension_grain(field: str) -> str | None:
    normalized = field.lower()
    grains = (
        ("country", ("country", "国家")),
        ("province", ("province", "省份", "省")),
        ("city", ("city", "城市", "市")),
        ("district", ("district", "county", "区县", "县")),
        ("store", ("store", "shop", "门店")),
        ("department", ("department", "dept", "部门")),
        ("category", ("category", "品类", "类别")),
    )
    for grain, tokens in grains:
        if any(token in normalized for token in tokens):
            return grain
    return None


def _cross_source_warnings(
    plan: DashboardPlan,
    datasets: Mapping[str, DatasetDefinition],
) -> tuple[str, ...]:
    time_entries: dict[str, tuple[str, str, str]] = {}
    dimension_entries: dict[str, tuple[str, str, str]] = {}
    for widget in plan.widgets:
        dataset = datasets[widget.dataset_id]
        source = dataset_source_key(dataset)
        types = {field.name: field.data_type for field in dataset.fields}
        for field in widget.dimensions:
            data_type = types.get(field)
            if data_type is None:
                continue
            if temporal := _temporal_grain(field, data_type):
                time_entries.setdefault(source, (dataset.name, field, temporal))
            elif dimension := _dimension_grain(field):
                dimension_entries.setdefault(source, (dataset.name, field, dimension))

    labels = {
        "year": "年",
        "quarter": "季度",
        "month": "月",
        "week": "周",
        "day": "日",
        "hour": "时刻",
        "country": "国家级",
        "province": "省级",
        "city": "城市级",
        "district": "区县级",
        "store": "门店级",
        "department": "部门级",
        "category": "品类级",
    }
    warnings: list[str] = []
    for title, entries in (
        ("时间粒度", time_entries),
        ("维度粒度", dimension_entries),
    ):
        grains = {entry[2] for entry in entries.values()}
        if len(entries) < 2 or len(grains) < 2:
            continue
        details = "、".join(
            f"{name}.{field}={labels[grain]}" for name, field, grain in entries.values()
        )
        warnings.append(
            f"跨来源{title}不一致（{details}）。如需合并，请先在源库视图或上游接口统一口径。"
        )
    return tuple(warnings)


def _rgb(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        return None
    try:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError:
        return None


def _luminance(color: tuple[int, int, int]) -> float:
    channels = []
    for item in color:
        value = item / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    first_luminance = _luminance(first)
    second_luminance = _luminance(second)
    lighter = max(first_luminance, second_luminance)
    darker = min(first_luminance, second_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _visual_issues(document: DashboardDocument) -> tuple[GenerationIssue, ...]:
    issues: list[GenerationIssue] = []
    canvas = document.canvas
    for component in document.components:
        frame = component.frame
        if (
            frame.x < 0
            or frame.y < 0
            or frame.x + frame.width > canvas.width
            or frame.y + frame.height > canvas.height
        ):
            issues.append(
                GenerationIssue(
                    code="VISUAL_OUT_OF_BOUNDS",
                    component_id=component.id,
                    field="frame",
                    message="组件超出画布边界",
                )
            )
        if frame.width < 80 or frame.height < 48:
            issues.append(
                GenerationIssue(
                    code="VISUAL_TOO_SMALL",
                    component_id=component.id,
                    field="frame",
                    message="组件小于可读尺寸",
                )
            )
        background = _rgb(component.style.get("background"))
        foreground = _rgb(component.style.get("color"))
        if background and foreground and _contrast_ratio(background, foreground) < 4.5:
            issues.append(
                GenerationIssue(
                    code="VISUAL_CONTRAST_LOW",
                    component_id=component.id,
                    field="style.color",
                    message="文本与背景对比度低于 4.5:1",
                )
            )

    for index, first in enumerate(document.components):
        a = first.frame
        for second in document.components[index + 1 :]:
            b = second.frame
            if (
                a.x < b.x + b.width
                and a.x + a.width > b.x
                and a.y < b.y + b.height
                and a.y + a.height > b.y
            ):
                issues.append(
                    GenerationIssue(
                        code="VISUAL_OVERLAP",
                        component_id=first.id,
                        field="frame",
                        message=f"组件与 {second.id} 重叠",
                    )
                )

    occupied = sum(item.frame.width * item.frame.height for item in document.components)
    area = canvas.width * canvas.height
    if area > 0 and occupied / area > 0.9:
        issues.append(
            GenerationIssue(
                code="VISUAL_DENSITY_HIGH",
                component_id=None,
                field="components",
                message="组件总面积超过画布的 90%",
            )
        )
    return tuple(issues)


def _placeholder(
    component: ComponentInstance, widget: PlanWidget, outcome: ExecutionOutcome
) -> ComponentInstance:
    message = "查询结果为空" if outcome.status == "empty" else "图表查询失败"
    return ComponentInstance(
        id=component.id,
        type="builtin.panel",
        frame=component.frame,
        state=component.state,
        props={
            "title": widget.title,
            "subtitle": message,
            "frame_variant": "plain",
            "show_grid": False,
        },
        style=component.style,
        interactions=component.interactions,
    )


class GenerationInspector:
    def inspect(
        self,
        plan: DashboardPlan,
        document: DashboardDocument,
        *,
        datasets: Mapping[str, DatasetDefinition],
        executions: Mapping[str, ExecutionOutcome],
    ) -> GenerationInspectionResult:
        components = {component.id: component for component in document.components}
        replacements: dict[str, ComponentInstance] = {}
        checks: list[WidgetSelfCheck] = []
        warnings = list(_cross_source_warnings(plan, datasets))
        execution_issues: list[GenerationIssue] = []

        for widget in plan.widgets:
            outcome = executions.get(widget.id)
            if outcome is None:
                outcome = ExecutionOutcome(
                    status="error", row_count=0, error_code="EXECUTION_MISSING"
                )
            check_issues: tuple[GenerationIssue, ...] = ()
            if outcome.status != "ok":
                code = "CHART_EMPTY" if outcome.status == "empty" else "CHART_EXECUTION_FAILED"
                issue = GenerationIssue(
                    code=code,
                    component_id=widget.id,
                    field="data_binding.chart_spec",
                    message=(
                        "图表查询结果为空"
                        if outcome.status == "empty"
                        else f"图表查询失败：{outcome.error_code or 'UNKNOWN'}"
                    ),
                )
                check_issues = (issue,)
                execution_issues.append(issue)
                warnings.append(f"组件 {widget.id} 已降级为占位：{issue.message}")
                if widget.id in components:
                    replacements[widget.id] = _placeholder(components[widget.id], widget, outcome)

            fields = _unique(
                [
                    *widget.dimensions,
                    *(item.field for item in widget.measures),
                    *(item.field for item in widget.filters),
                ]
            )
            checks.append(
                WidgetSelfCheck(
                    widget_id=widget.id,
                    dataset_id=widget.dataset_id,
                    fields=fields,
                    aggregations=tuple(
                        f"{item.field}:{item.aggregation.value}" for item in widget.measures
                    ),
                    filters=tuple(f"{item.field}:{item.operator.value}" for item in widget.filters),
                    row_count=outcome.row_count,
                    status=outcome.status,
                    issues=check_issues,
                )
            )

        updated_components = tuple(
            replacements.get(component.id, component) for component in document.components
        )
        updated_document = document.model_copy(update={"components": updated_components})
        issues = (
            *execution_issues,
            *_semantic_issues(plan, datasets),
            *_visual_issues(updated_document),
        )
        report = GenerationSelfCheckReport(
            valid=not issues,
            widget_count=len(plan.widgets),
            executed_count=len(executions),
            fallback_count=len(replacements),
            checks=tuple(checks),
            issues=issues,
        )
        return GenerationInspectionResult(
            document=updated_document,
            report=report,
            warnings=tuple(warnings),
        )


__all__ = [
    "ExecutionOutcome",
    "GenerationInspectionResult",
    "GenerationInspector",
    "GenerationIssue",
    "GenerationSelfCheckReport",
    "WidgetSelfCheck",
]
