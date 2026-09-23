from typing import Literal

from pydantic import Field

from datapulse.contracts.common import ContractModel, NonBlankStr


class GenerationIssue(ContractModel):
    code: NonBlankStr
    component_id: str | None = None
    field: NonBlankStr
    message: NonBlankStr


class WidgetSelfCheck(ContractModel):
    widget_id: NonBlankStr
    dataset_id: NonBlankStr
    fields: tuple[str, ...] = Field(default_factory=tuple)
    aggregations: tuple[str, ...] = Field(default_factory=tuple)
    filters: tuple[str, ...] = Field(default_factory=tuple)
    row_count: int = Field(ge=0)
    status: Literal["ok", "empty", "error"]
    issues: tuple[GenerationIssue, ...] = Field(default_factory=tuple)


class GenerationSelfCheckReport(ContractModel):
    valid: bool
    widget_count: int = Field(ge=0)
    executed_count: int = Field(ge=0)
    fallback_count: int = Field(ge=0)
    checks: tuple[WidgetSelfCheck, ...] = Field(default_factory=tuple)
    issues: tuple[GenerationIssue, ...] = Field(default_factory=tuple)


__all__ = ["GenerationIssue", "GenerationSelfCheckReport", "WidgetSelfCheck"]
