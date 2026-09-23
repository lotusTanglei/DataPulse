from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.generation import GenerationSelfCheckReport
from datapulse.screen.access import ScreenAccessPolicy


class ScreenCreate(ContractModel):
    name: NonBlankStr
    description: str = ""
    draft_document: DashboardDocument | None = None


class DashboardPlanCompileRequest(ContractModel):
    plan: DashboardPlan
    canvas_width: int = Field(default=1920, ge=1, le=7680)
    canvas_height: int = Field(default=1080, ge=1, le=7680)


class DashboardPlanCompileResponse(ContractModel):
    plan: DashboardPlan
    document: DashboardDocument
    report: GenerationSelfCheckReport | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class DashboardPlanRecompileRequest(ContractModel):
    previous_plan: DashboardPlan
    plan: DashboardPlan
    document: DashboardDocument
    affected_region_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=12)


class DashboardPlanRecompileResponse(ContractModel):
    plan: DashboardPlan
    document: DashboardDocument
    affected_region_ids: tuple[NonBlankStr, ...]
    report: GenerationSelfCheckReport | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class ScreenDraftUpdate(ContractModel):
    name: NonBlankStr | None = None
    description: str | None = None
    draft_document: DashboardDocument | None = None
    access_policy: ScreenAccessPolicy | None = None
    expected_revision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if (
            self.name is None
            and self.description is None
            and self.draft_document is None
            and self.access_policy is None
        ):
            raise ValueError("At least one screen field must be updated.")
        if self.draft_document is not None and self.expected_revision is None:
            raise ValueError("expected_revision is required when saving a draft.")
        if self.draft_document is None and self.expected_revision is not None:
            raise ValueError("expected_revision is only valid when saving a draft.")
        return self


class ScreenPublish(ContractModel):
    expected_revision: int = Field(ge=0)


class ScreenSummary(ContractModel):
    id: str
    name: NonBlankStr
    description: str
    draft_revision: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScreenResponse(ScreenSummary):
    draft_document: DashboardDocument
    published_document: DashboardDocument | None
    access_policy: ScreenAccessPolicy
