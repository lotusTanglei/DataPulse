from typing import Annotated, Literal

from pydantic import Field

from datapulse.contracts.chart import ChartSpec, ChartType, Filter, Measure, Sort
from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
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
    question: NonBlankStr = Field(max_length=4000)
    dataset_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=8)
    mode: Literal["analysis", "chart"] = "analysis"


class AiAnalysisDraft(ContractModel):
    plan: AnalysisPlan
    narrative: NonBlankStr
    chart_spec: ChartSpec | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class AiAnalysisResponse(AiAnalysisDraft):
    preview: QueryResult


class AiChartRequest(ContractModel):
    question: NonBlankStr = Field(max_length=4000)
    dataset_id: NonBlankStr
    target_component_type: ChartType | None = None


class AiChartResponse(ContractModel):
    chart_spec: ChartSpec
    explanation: NonBlankStr
    preview: QueryResult
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class AiScreenRequest(ContractModel):
    question: NonBlankStr = Field(max_length=4000)
    dataset_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=8)
    canvas_width: int = Field(default=1920, ge=1, le=7680)
    canvas_height: int = Field(default=1080, ge=1, le=7680)
    theme: Literal["dark", "light"] = "dark"


class AiScreenResponse(ContractModel):
    document: DashboardDocument
    explanation: NonBlankStr
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class AiUpdateFrameCommand(ContractModel):
    type: Literal["update_frame"] = "update_frame"
    component_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=8)
    patch: dict[str, JsonValue] = Field(min_length=1, max_length=5)


class AiUpdatePropsCommand(ContractModel):
    type: Literal["update_props"] = "update_props"
    component_id: NonBlankStr
    patch: dict[str, JsonValue] = Field(min_length=1, max_length=8)


class AiUpdateStyleCommand(ContractModel):
    type: Literal["update_style"] = "update_style"
    component_id: NonBlankStr
    patch: dict[str, JsonValue] = Field(min_length=1, max_length=8)


class AiUpdateDataBindingCommand(ContractModel):
    type: Literal["update_data_binding"] = "update_data_binding"
    component_id: NonBlankStr
    data_binding: dict[str, JsonValue]


class AiSetComponentStateCommand(ContractModel):
    type: Literal["set_component_state"] = "set_component_state"
    component_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=8)
    patch: dict[str, JsonValue] = Field(min_length=1, max_length=3)


AiEditCommand = Annotated[
    AiUpdateFrameCommand
    | AiUpdatePropsCommand
    | AiUpdateStyleCommand
    | AiUpdateDataBindingCommand
    | AiSetComponentStateCommand,
    Field(discriminator="type"),
]


class AiEditRequest(ContractModel):
    question: NonBlankStr = Field(max_length=4000)
    document: DashboardDocument
    selected_component_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=8)
    dataset_ids: tuple[NonBlankStr, ...] = Field(default_factory=tuple, max_length=8)


class AiEditResponse(ContractModel):
    commands: tuple[AiEditCommand, ...] = Field(min_length=1, max_length=8)
    explanation: NonBlankStr
    warnings: tuple[str, ...] = Field(default_factory=tuple)
