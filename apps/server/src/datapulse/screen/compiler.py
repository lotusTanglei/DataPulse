from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Set
from math import ceil

from datapulse.contracts.chart import ChartSpec, ChartType, VisualSpec
from datapulse.contracts.common import JsonValue
from datapulse.contracts.dashboard import (
    Canvas,
    ComponentInstance,
    DashboardDocument,
    Frame,
    Theme,
)
from datapulse.contracts.dashboard_plan import DashboardPlan, PlanRegion, PlanWidget
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.screen.grid import GridCell, GridSystem
from datapulse.screen.planning import (
    PlanValidationError,
    PlanValidationIssue,
    PlanValidationResult,
    PlanValidator,
)
from datapulse.screen.sources import dataset_source_key
from datapulse.screen.templates import TEMPLATE_SKELETONS, RegionSlot, TemplateSkeleton

_COMPONENT_TYPES = {
    ChartType.AREA: "builtin.line",
    ChartType.BAR: "builtin.bar",
    ChartType.FUNNEL: "builtin.funnel",
    ChartType.GAUGE: "builtin.gauge",
    ChartType.HEATMAP: "builtin.heatmap",
    ChartType.KPI: "builtin.kpi",
    ChartType.LINE: "builtin.line",
    ChartType.MAP: "builtin.geo_map",
    ChartType.PIE: "builtin.pie",
    ChartType.PROGRESS: "builtin.progress",
    ChartType.RADAR: "builtin.radar",
    ChartType.SCATTER: "builtin.scatter",
    ChartType.TABLE: "builtin.table",
}


def _props(widget: PlanWidget) -> dict[str, JsonValue]:
    props: dict[str, JsonValue] = {"empty_text": "暂无数据"}
    if widget.chart_type in {ChartType.KPI, ChartType.GAUGE, ChartType.PROGRESS}:
        props.update({"label": widget.title, "precision": 0})
    elif widget.chart_type is ChartType.TABLE:
        props["max_rows"] = min(widget.limit, 100)
    elif widget.chart_type is ChartType.BAR:
        props["orientation"] = "vertical"
    elif widget.chart_type is ChartType.PIE:
        props["variant"] = "pie"
    return props


def _per_row(
    region: PlanRegion,
    *,
    widget_count: int,
    skeleton: TemplateSkeleton,
    density: str,
) -> int:
    base = skeleton.region_columns[region.kind]
    maximum = 6 if density == "compact" else 4
    if widget_count > base * 2:
        base = min(maximum, 4)
    return max(1, min(base, widget_count))


def _group_by_source(
    widgets: list[PlanWidget],
    datasets: Mapping[str, DatasetDefinition],
) -> list[PlanWidget]:
    grouped: dict[str, list[PlanWidget]] = {}
    for widget in widgets:
        key = dataset_source_key(datasets[widget.dataset_id])
        grouped.setdefault(key, []).append(widget)
    return [widget for group in grouped.values() for widget in group]


def _weighted_spans(total: int, weights: list[int]) -> list[int]:
    spans: list[int] = []
    remaining = total
    remaining_weight = sum(weights)
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            spans.append(remaining)
            break
        span = max(1, remaining * weight // remaining_weight)
        span = min(span, remaining - (len(weights) - index - 1))
        spans.append(span)
        remaining -= span
        remaining_weight -= weight
    return spans


class DocumentCompiler:
    def __init__(self, *, validator: PlanValidator | None = None) -> None:
        self._validator = validator or PlanValidator()

    def compile(
        self,
        plan: DashboardPlan,
        *,
        datasets: Mapping[str, DatasetDefinition],
        authorized_dataset_ids: Set[str],
        canvas_width: int = 1920,
        canvas_height: int = 1080,
    ) -> DashboardDocument:
        self._validator.validate_or_raise(
            plan,
            datasets=datasets,
            authorized_dataset_ids=authorized_dataset_ids,
        )
        skeleton = TEMPLATE_SKELETONS[plan.layout.template]
        theme_tokens = skeleton.theme_tokens[plan.layout.theme]
        widgets_by_region: dict[str, list[PlanWidget]] = defaultdict(list)
        for widget in plan.widgets:
            widgets_by_region[widget.region_id].append(widget)
        for region_id, widgets in widgets_by_region.items():
            widgets_by_region[region_id] = _group_by_source(widgets, datasets)

        active_regions = [
            region
            for region in sorted(plan.regions, key=lambda item: (item.order, item.id))
            if widgets_by_region[region.id]
        ]
        content_top = skeleton.safe_margin_y + skeleton.title_height + skeleton.slot_gap
        content_height = canvas_height - content_top - skeleton.safe_margin_y
        content_width = canvas_width - skeleton.safe_margin_x * 2
        regions_by_kind: dict[str, list[PlanRegion]] = defaultdict(list)
        for region in active_regions:
            regions_by_kind[region.kind].append(region)
        active_slots_by_band: dict[int, list[tuple[str, RegionSlot]]] = defaultdict(list)
        for kind in regions_by_kind:
            slot = skeleton.region_slots[kind]
            active_slots_by_band[slot.band].append((kind, slot))
        bands = sorted(active_slots_by_band)
        band_weights = [active_slots_by_band[band][0][1].band_weight for band in bands]
        outer_grid = GridSystem(
            canvas_width=content_width,
            canvas_height=content_height,
            columns=plan.layout.grid_columns,
            rows=sum(band_weights),
            margin=0,
            gutter=skeleton.slot_gap,
        )
        region_frames: dict[str, Frame] = {}
        band_row = 0
        for band, band_weight in zip(bands, band_weights, strict=True):
            slots = sorted(
                active_slots_by_band[band],
                key=lambda item: (item[1].column_order, item[0]),
            )
            column_spans = _weighted_spans(
                plan.layout.grid_columns,
                [slot.column_weight for _, slot in slots],
            )
            column = 0
            for (kind, _slot), column_span in zip(slots, column_spans, strict=True):
                slot_frame = outer_grid.frame(
                    GridCell(
                        column=column,
                        row=band_row,
                        column_span=column_span,
                        row_span=band_weight,
                    )
                )
                column += column_span
                regions = regions_by_kind[kind]
                region_grid = GridSystem(
                    canvas_width=slot_frame.width,
                    canvas_height=slot_frame.height,
                    columns=plan.layout.grid_columns,
                    rows=len(regions),
                    margin=0,
                    gutter=skeleton.slot_gap,
                )
                for index, region in enumerate(regions):
                    relative = region_grid.frame(
                        GridCell(
                            column=0,
                            row=index,
                            column_span=plan.layout.grid_columns,
                            row_span=1,
                        )
                    )
                    region_frames[region.id] = Frame(
                        x=round(slot_frame.x + relative.x, 4),
                        y=round(slot_frame.y + relative.y, 4),
                        width=relative.width,
                        height=relative.height,
                    )
            band_row += band_weight

        components: list[ComponentInstance] = [
            ComponentInstance(
                id="plan-title",
                type="builtin.text",
                frame=Frame(
                    x=skeleton.safe_margin_x,
                    y=skeleton.safe_margin_y,
                    width=content_width,
                    height=skeleton.title_height,
                    z_index=1,
                ),
                props={
                    "text": plan.title,
                    "align": "left",
                    "font_size": theme_tokens["title_font_size"],
                },
                style={"color": theme_tokens["text_primary"]},
            )
        ]

        for region in active_regions:
            region_frame = region_frames[region.id]
            per_row = _per_row(
                region,
                widget_count=len(widgets_by_region[region.id]),
                skeleton=skeleton,
                density=plan.layout.density,
            )
            rows = ceil(len(widgets_by_region[region.id]) / per_row)
            grid = GridSystem(
                canvas_width=region_frame.width,
                canvas_height=region_frame.height,
                columns=plan.layout.grid_columns,
                rows=rows,
                margin=0,
                gutter=skeleton.slot_gap,
            )
            column_span = plan.layout.grid_columns // per_row
            for index, widget in enumerate(widgets_by_region[region.id]):
                relative = grid.frame(
                    GridCell(
                        column=(index % per_row) * column_span,
                        row=index // per_row,
                        column_span=column_span,
                        row_span=1,
                        z_index=1,
                    )
                )
                chart_spec = ChartSpec(
                    dataset_id=widget.dataset_id,
                    dimensions=widget.dimensions,
                    measures=widget.measures,
                    filters=widget.filters,
                    sort=widget.sort,
                    limit=widget.limit,
                    visual=VisualSpec(type=widget.chart_type, title=widget.title),
                )
                components.append(
                    ComponentInstance(
                        id=widget.id,
                        type=_COMPONENT_TYPES[widget.chart_type],
                        frame=Frame(
                            x=round(relative.x + region_frame.x + skeleton.safe_margin_x, 4),
                            y=round(relative.y + region_frame.y + content_top, 4),
                            width=relative.width,
                            height=relative.height,
                            z_index=relative.z_index,
                        ),
                        props=_props(widget),
                        style={
                            "background": theme_tokens["panel_background"],
                            "border_color": theme_tokens["panel_border"],
                            "color": theme_tokens["text_primary"],
                        },
                        data_binding={"chart_spec": chart_spec.model_dump(mode="json")},
                    )
                )

        return DashboardDocument(
            canvas=Canvas(
                width=canvas_width,
                height=canvas_height,
                background={"color": theme_tokens["canvas_background"]},
            ),
            theme=Theme(
                id=f"datapulse-{plan.layout.theme}",
                tokens=dict(theme_tokens),
            ),
            parameters=plan.parameters,
            components=tuple(components),
        )

    def recompile_regions(
        self,
        *,
        previous_plan: DashboardPlan,
        plan: DashboardPlan,
        document: DashboardDocument,
        affected_region_ids: Set[str],
        datasets: Mapping[str, DatasetDefinition],
        authorized_dataset_ids: Set[str],
    ) -> DashboardDocument:
        self._validator.validate_or_raise(
            plan,
            datasets=datasets,
            authorized_dataset_ids=authorized_dataset_ids,
        )
        known_region_ids = {
            *(region.id for region in previous_plan.regions),
            *(region.id for region in plan.regions),
        }
        if not affected_region_ids or not affected_region_ids <= known_region_ids:
            self._raise_scope_invalid(
                field="affected_region_ids",
                reason="受影响分区为空或包含未知分区",
                expected="当前规划中的一个或多个分区 ID",
            )

        all_regions_affected = known_region_ids <= affected_region_ids
        if not all_regions_affected:
            self._validate_partial_scope(
                previous_plan=previous_plan,
                plan=plan,
                affected_region_ids=affected_region_ids,
            )

        compiled = self.compile(
            plan,
            datasets=datasets,
            authorized_dataset_ids=authorized_dataset_ids,
            canvas_width=document.canvas.width,
            canvas_height=document.canvas.height,
        )
        if all_regions_affected:
            return compiled

        previous_compiled = self.compile(
            previous_plan,
            datasets=datasets,
            authorized_dataset_ids={*previous_plan.dataset_ids},
            canvas_width=document.canvas.width,
            canvas_height=document.canvas.height,
        )
        previous_widgets = {widget.id: widget for widget in previous_plan.widgets}
        next_widgets = {widget.id: widget for widget in plan.widgets}
        previous_canonical = {component.id: component for component in previous_compiled.components}
        next_canonical = {component.id: component for component in compiled.components}
        for widget_id, widget in next_widgets.items():
            if widget.region_id in affected_region_ids:
                continue
            previous_component = previous_canonical.get(widget_id)
            next_component = next_canonical.get(widget_id)
            if (
                previous_component is None
                or next_component is None
                or previous_component.model_copy(update={"frame": next_component.frame})
                != next_component
            ):
                self._raise_scope_invalid(
                    field=f"widgets.{widget_id}",
                    reason="局部修改会改变未选分区的内容或样式",
                    expected="未选分区除自动布局外的编译结果保持不变",
                )

        current_components = {component.id: component for component in document.components}
        next_regions = {region.id: region for region in plan.regions}
        skeleton = TEMPLATE_SKELETONS[plan.layout.template]
        affected_components: dict[str, ComponentInstance] = {}
        ordered_widget_ids = [
            component.id for component in compiled.components if component.id in next_widgets
        ]
        for region_id in affected_region_ids:
            region = next_regions.get(region_id)
            region_widget_ids = [
                widget_id
                for widget_id in ordered_widget_ids
                if next_widgets[widget_id].region_id == region_id
            ]
            if region is None or not region_widget_ids:
                continue
            previous_region_components = [
                current_components[widget.id]
                for widget in previous_plan.widgets
                if widget.region_id == region_id and widget.id in current_components
            ]
            if not previous_region_components:
                self._raise_scope_invalid(
                    field=f"regions.{region_id}",
                    reason="局部修改无法为新增分区分配独立空间",
                    expected="选择整屏修改，或使用已有非空分区",
                )
            left = min(component.frame.x for component in previous_region_components)
            top = min(component.frame.y for component in previous_region_components)
            right = max(
                component.frame.x + component.frame.width
                for component in previous_region_components
            )
            bottom = max(
                component.frame.y + component.frame.height
                for component in previous_region_components
            )
            per_row = _per_row(
                region,
                widget_count=len(region_widget_ids),
                skeleton=skeleton,
                density=plan.layout.density,
            )
            rows = ceil(len(region_widget_ids) / per_row)
            try:
                grid = GridSystem(
                    canvas_width=right - left,
                    canvas_height=bottom - top,
                    columns=plan.layout.grid_columns,
                    rows=rows,
                    margin=0,
                    gutter=skeleton.slot_gap,
                )
            except ValueError:
                self._raise_scope_invalid(
                    field=f"regions.{region_id}",
                    reason="受影响分区无法容纳修改后的组件",
                    expected="减少组件数量，或选择整屏修改以重新分配空间",
                )
            column_span = plan.layout.grid_columns // per_row
            for index, widget_id in enumerate(region_widget_ids):
                relative = grid.frame(
                    GridCell(
                        column=(index % per_row) * column_span,
                        row=index // per_row,
                        column_span=column_span,
                        row_span=1,
                        z_index=next_canonical[widget_id].frame.z_index,
                    )
                )
                affected_components[widget_id] = next_canonical[widget_id].model_copy(
                    update={
                        "frame": Frame(
                            x=round(left + relative.x, 4),
                            y=round(top + relative.y, 4),
                            width=relative.width,
                            height=relative.height,
                            z_index=relative.z_index,
                        )
                    }
                )

        components = []
        for component in compiled.components:
            widget = next_widgets.get(component.id)
            if widget is None:
                components.append(current_components.get(component.id, component))
            elif widget.region_id in affected_region_ids:
                components.append(affected_components[component.id])
            else:
                current = current_components.get(component.id)
                if current is None or component.id not in previous_widgets:
                    self._raise_scope_invalid(
                        field=f"document.components.{component.id}",
                        reason="未选分区缺少可保留的原组件",
                        expected="与上一版规划一致的组件",
                    )
                components.append(current)
        return compiled.model_copy(update={"components": tuple(components)})

    @staticmethod
    def _validate_partial_scope(
        *,
        previous_plan: DashboardPlan,
        plan: DashboardPlan,
        affected_region_ids: Set[str],
    ) -> None:
        global_fields = ("title", "audience", "narrative", "dataset_ids", "layout", "parameters")
        for field in global_fields:
            if getattr(previous_plan, field) != getattr(plan, field):
                DocumentCompiler._raise_scope_invalid(
                    field=field,
                    reason="整屏属性不能在局部分区修改中变更",
                    expected="选择整屏修改，或保持整屏属性不变",
                )

        previous_regions = {region.id: region for region in previous_plan.regions}
        next_regions = {region.id: region for region in plan.regions}
        for region_id in set(previous_regions) | set(next_regions):
            if region_id not in affected_region_ids and previous_regions.get(
                region_id
            ) != next_regions.get(region_id):
                DocumentCompiler._raise_scope_invalid(
                    field=f"regions.{region_id}",
                    reason="未选分区定义发生变化",
                    expected="只有受影响分区可以修改",
                )

        previous_widgets = {widget.id: widget for widget in previous_plan.widgets}
        next_widgets = {widget.id: widget for widget in plan.widgets}
        for widget_id in set(previous_widgets) | set(next_widgets):
            previous_widget = previous_widgets.get(widget_id)
            next_widget = next_widgets.get(widget_id)
            if previous_widget == next_widget:
                continue
            region_ids = {
                widget.region_id for widget in (previous_widget, next_widget) if widget is not None
            }
            if not region_ids <= affected_region_ids:
                DocumentCompiler._raise_scope_invalid(
                    field=f"widgets.{widget_id}",
                    reason="组件修改超出声明的受影响分区",
                    expected="只修改受影响分区内的组件",
                )

    @staticmethod
    def _raise_scope_invalid(*, field: str, reason: str, expected: str) -> None:
        raise PlanValidationError(
            PlanValidationResult(
                valid=False,
                issues=(
                    PlanValidationIssue(
                        code="PLAN_RECOMPILE_SCOPE_INVALID",
                        widget_id=None,
                        field=field,
                        reason=reason,
                        expected=expected,
                    ),
                ),
            )
        )


__all__ = ["DocumentCompiler"]
