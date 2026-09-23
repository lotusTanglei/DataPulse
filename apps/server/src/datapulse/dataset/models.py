from datetime import datetime

from pydantic import Field, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dataset import (
    DatasetDefinition,
    DatasetFieldOverride,
    DatasetParameter,
    RestQuery,
)


class DatasetCreate(ContractModel):
    name: NonBlankStr
    data_source_id: NonBlankStr
    sql: NonBlankStr | None = None
    query: RestQuery | None = None
    parameters: tuple[DatasetParameter, ...] = Field(default_factory=tuple)
    max_rows: int = Field(default=5000, ge=1, le=5000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)

    @model_validator(mode="after")
    def require_query(self) -> "DatasetCreate":
        if (self.sql is None) == (self.query is None):
            raise ValueError("Exactly one of sql or query must be provided.")
        return self


class DatasetUpdate(ContractModel):
    name: NonBlankStr | None = None
    sql: NonBlankStr | None = None
    query: RestQuery | None = None
    parameters: tuple[DatasetParameter, ...] | None = None
    profile_overrides: tuple[DatasetFieldOverride, ...] | None = None
    max_rows: int | None = Field(default=None, ge=1, le=5000)
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)

    @model_validator(mode="after")
    def require_change(self) -> "DatasetUpdate":
        if all(
            value is None
            for value in (
                self.name,
                self.sql,
                self.query,
                self.parameters,
                self.profile_overrides,
                self.max_rows,
                self.timeout_seconds,
            )
        ):
            raise ValueError("At least one dataset field must be updated.")
        return self


class DatasetPreviewRequest(ContractModel):
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class DatasetResponse(ContractModel):
    id: str
    name: NonBlankStr
    data_source_id: str | None
    definition: DatasetDefinition
    created_at: datetime
    updated_at: datetime
