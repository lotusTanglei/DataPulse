from typing import Literal

from pydantic import Field

from datapulse.contracts.chart import ChartSpec, ChartType, Filter, Measure, Sort
from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.query.models import QueryResult


class AnalysisPlan(ContractModel):
    schema_version: Literal[1] = 1
    question: NonBlankStr
    dataset_ids: tuple[NonBlankStr, ...] = Field(min_length=1)
    dimensions: tuple[NonBlankStr, ...] = Field(default_factory=tuple)
    measures: tuple[Measure, ...] = Field(default_factory=tuple)
    filters: tuple[Filter, ...] = Field(default_factory=tuple)
    sort: tuple[Sort, ...] = Field(default_factory=tuple)
    recommended_chart: ChartType
    assumptions: tuple[str, ...] = Field(default_factory=tuple)
    requires_confirmation: bool = True


class AiAnalysisRequest(ContractModel):
    question: NonBlankStr
    dataset_ids: tuple[NonBlankStr, ...] = Field(min_length=1)
    mode: Literal["analysis", "chart"] = "analysis"


class AiAnalysisResponse(ContractModel):
    plan: AnalysisPlan
    narrative: NonBlankStr
    chart_spec: ChartSpec | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class AiChartRequest(ContractModel):
    question: NonBlankStr
    dataset_id: NonBlankStr
    target_component_type: ChartType | None = None


class AiChartResponse(ContractModel):
    chart_spec: ChartSpec
    explanation: NonBlankStr
    preview: QueryResult
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class AiScreenRequest(ContractModel):
    question: NonBlankStr
    dataset_ids: tuple[NonBlankStr, ...] = Field(min_length=1)
    canvas_width: int = Field(default=1920, ge=1)
    canvas_height: int = Field(default=1080, ge=1)
    theme: Literal["dark", "light"] = "dark"


class AiScreenResponse(ContractModel):
    document: DashboardDocument
    explanation: NonBlankStr
    warnings: tuple[str, ...] = Field(default_factory=tuple)
