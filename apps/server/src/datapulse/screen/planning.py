from collections import Counter
from collections.abc import Mapping, Set

from pydantic import Field

from datapulse.contracts.chart import Aggregation, ChartType
from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.contracts.dashboard_plan import DashboardPlan, PlanWidget
from datapulse.contracts.dataset import DatasetDefinition, DataType

MAX_WIDGETS_PER_REGION = 16


class PlanValidationIssue(ContractModel):
    code: NonBlankStr
    widget_id: str | None = None
    field: NonBlankStr
    reason: NonBlankStr
    expected: NonBlankStr


class PlanValidationResult(ContractModel):
    valid: bool
    issues: tuple[PlanValidationIssue, ...] = Field(default_factory=tuple)


class PlanValidationError(ValueError):
    def __init__(self, result: PlanValidationResult) -> None:
        super().__init__("Dashboard plan validation failed.")
        self.result = result


def _issue(
    code: str,
    *,
    widget_id: str | None,
    field: str,
    reason: str,
    expected: str,
) -> PlanValidationIssue:
    return PlanValidationIssue(
        code=code,
        widget_id=widget_id,
        field=field,
        reason=reason,
        expected=expected,
    )


def _shape_valid(widget: PlanWidget) -> bool:
    dimension_count = len(widget.dimensions)
    measure_count = len(widget.measures)
    if widget.chart_type in {
        ChartType.LINE,
        ChartType.AREA,
        ChartType.BAR,
        ChartType.RADAR,
        ChartType.HEATMAP,
        ChartType.SCATTER,
        ChartType.FUNNEL,
    }:
        return dimension_count >= 1 and measure_count >= 1
    if widget.chart_type in {ChartType.PIE, ChartType.MAP}:
        return dimension_count == 1 and measure_count >= 1
    if widget.chart_type in {ChartType.KPI, ChartType.PROGRESS, ChartType.GAUGE}:
        return dimension_count <= 1 and measure_count == 1
    return dimension_count + measure_count >= 1


class PlanValidator:
    def validate(
        self,
        plan: DashboardPlan,
        *,
        datasets: Mapping[str, DatasetDefinition],
        authorized_dataset_ids: Set[str],
    ) -> PlanValidationResult:
        issues: list[PlanValidationIssue] = []
        region_counts = Counter(widget.region_id for widget in plan.widgets)
        for region_id, count in region_counts.items():
            if count > MAX_WIDGETS_PER_REGION:
                issues.append(
                    _issue(
                        "PLAN_REGION_DENSITY_INVALID",
                        widget_id=None,
                        field=f"regions.{region_id}",
                        reason=f"分区 {region_id} 包含 {count} 个组件，超过可读密度",
                        expected=f"每个分区不超过 {MAX_WIDGETS_PER_REGION} 个组件",
                    )
                )

        for widget in plan.widgets:
            if widget.dataset_id not in authorized_dataset_ids:
                issues.append(
                    _issue(
                        "PLAN_DATASET_UNAUTHORIZED",
                        widget_id=widget.id,
                        field="dataset_id",
                        reason=f"数据集 {widget.dataset_id} 不存在或未授权",
                        expected="当前用户可访问的数据集",
                    )
                )
                continue
            dataset = datasets.get(widget.dataset_id)
            if dataset is None:
                issues.append(
                    _issue(
                        "PLAN_DATASET_UNKNOWN",
                        widget_id=widget.id,
                        field="dataset_id",
                        reason=f"数据集 {widget.dataset_id} 不存在",
                        expected="已登记的数据集",
                    )
                )
                continue

            fields = {field.name: field.data_type for field in dataset.fields}
            expected_fields = ", ".join(fields)
            requested = [
                *((f"dimensions[{index}]", field) for index, field in enumerate(widget.dimensions)),
                *(
                    (f"measures[{index}].field", item.field)
                    for index, item in enumerate(widget.measures)
                ),
                *(
                    (f"filters[{index}].field", item.field)
                    for index, item in enumerate(widget.filters)
                ),
                *((f"sort[{index}].field", item.field) for index, item in enumerate(widget.sort)),
            ]
            for path, field in requested:
                if field not in fields:
                    issues.append(
                        _issue(
                            "PLAN_FIELD_UNKNOWN",
                            widget_id=widget.id,
                            field=path,
                            reason=f"字段 {field} 不存在于数据集 {widget.dataset_id}",
                            expected=expected_fields,
                        )
                    )

            for index, measure in enumerate(widget.measures):
                data_type = fields.get(measure.field)
                valid_types = {DataType.INTEGER, DataType.NUMBER}
                if measure.aggregation in {Aggregation.MINIMUM, Aggregation.MAXIMUM}:
                    valid_types |= {DataType.DATE, DataType.DATETIME}
                if (
                    data_type is not None
                    and measure.aggregation is not Aggregation.COUNT
                    and data_type not in valid_types
                ):
                    issues.append(
                        _issue(
                            "PLAN_AGGREGATION_INVALID",
                            widget_id=widget.id,
                            field=f"measures[{index}].aggregation",
                            reason=(
                                f"字段 {measure.field} 的类型 {data_type.value} "
                                f"不支持 {measure.aggregation.value} 聚合"
                            ),
                            expected="数值字段使用 sum/avg/min/max，其他字段使用 count",
                        )
                    )

            if not _shape_valid(widget):
                issues.append(
                    _issue(
                        "PLAN_SHAPE_INVALID",
                        widget_id=widget.id,
                        field="chart_type",
                        reason=f"图表 {widget.chart_type.value} 的维度和指标数量不匹配",
                        expected="符合图表类型要求的维度与指标组合",
                    )
                )

        return PlanValidationResult(valid=not issues, issues=tuple(issues))

    def validate_or_raise(
        self,
        plan: DashboardPlan,
        *,
        datasets: Mapping[str, DatasetDefinition],
        authorized_dataset_ids: Set[str],
    ) -> None:
        result = self.validate(
            plan,
            datasets=datasets,
            authorized_dataset_ids=authorized_dataset_ids,
        )
        if not result.valid:
            raise PlanValidationError(result)


__all__ = [
    "MAX_WIDGETS_PER_REGION",
    "PlanValidationError",
    "PlanValidationIssue",
    "PlanValidationResult",
    "PlanValidator",
]
