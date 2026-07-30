from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.contracts.dashboard import DashboardDocument


class ScreenCreate(ContractModel):
    name: NonBlankStr
    description: str = ""


class ScreenDraftUpdate(ContractModel):
    name: NonBlankStr | None = None
    description: str | None = None
    draft_document: DashboardDocument | None = None
    expected_revision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if self.name is None and self.description is None and self.draft_document is None:
            raise ValueError("At least one screen field must be updated.")
        if self.draft_document is not None and self.expected_revision is None:
            raise ValueError("expected_revision is required when saving a draft.")
        if self.draft_document is None and self.expected_revision is not None:
            raise ValueError("expected_revision is only valid when saving a draft.")
        return self


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
