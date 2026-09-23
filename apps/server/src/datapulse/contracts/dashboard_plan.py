from typing import Literal, Self

from pydantic import Field, model_validator

from datapulse.contracts.chart import ChartType, Filter, Measure, Sort
from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.contracts.dashboard import DashboardParameter


class PlanLayout(ContractModel):
    template: Literal[
        "executive-overview",
        "trend-focus",
        "comparison-board",
        "status-wall",
        "analysis-lab",
    ] = "executive-overview"
    grid_columns: Literal[12, 24] = 24
    density: Literal["comfortable", "compact"] = "comfortable"
    theme: Literal["dark", "light"] = "dark"


class PlanRegion(ContractModel):
    id: NonBlankStr
    kind: Literal["header", "summary", "main", "secondary", "sidebar", "footer"]
    title: str = ""
    order: int = Field(default=0, ge=0)


class PlanWidget(ContractModel):
    id: NonBlankStr
    title: NonBlankStr
    intent: NonBlankStr
    region_id: NonBlankStr
    dataset_id: NonBlankStr
    chart_type: ChartType
    dimensions: tuple[NonBlankStr, ...] = Field(default_factory=tuple, max_length=3)
    measures: tuple[Measure, ...] = Field(default_factory=tuple, max_length=4)
    filters: tuple[Filter, ...] = Field(default_factory=tuple, max_length=12)
    sort: tuple[Sort, ...] = Field(default_factory=tuple, max_length=4)
    limit: int = Field(default=1000, ge=1, le=5000)


class DashboardPlan(ContractModel):
    schema_version: Literal[1] = 1
    title: NonBlankStr
    audience: NonBlankStr
    narrative: NonBlankStr
    dataset_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=8)
    layout: PlanLayout = Field(default_factory=PlanLayout)
    regions: tuple[PlanRegion, ...] = Field(min_length=1, max_length=12)
    widgets: tuple[PlanWidget, ...] = Field(min_length=1, max_length=40)
    parameters: tuple[DashboardParameter, ...] = Field(default_factory=tuple, max_length=12)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        dataset_ids = list(self.dataset_ids)
        if len(dataset_ids) != len(set(dataset_ids)):
            raise ValueError("dataset IDs must be unique")

        region_ids = [region.id for region in self.regions]
        if len(region_ids) != len(set(region_ids)):
            raise ValueError("region IDs must be unique")

        widget_ids = [widget.id for widget in self.widgets]
        if len(widget_ids) != len(set(widget_ids)):
            raise ValueError("widget IDs must be unique")

        known_regions = set(region_ids)
        known_datasets = set(dataset_ids)
        for widget in self.widgets:
            if widget.region_id not in known_regions:
                raise ValueError(f"widget references unknown region {widget.region_id!r}")
            if widget.dataset_id not in known_datasets:
                raise ValueError(f"widget references unknown dataset {widget.dataset_id!r}")
        return self


__all__ = [
    "DashboardPlan",
    "PlanLayout",
    "PlanRegion",
    "PlanWidget",
]
