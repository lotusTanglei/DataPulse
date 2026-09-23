from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, StrictBool, StringConstraints, model_validator

from datapulse.contracts.common import ContractModel

type Role = Literal["admin", "editor", "viewer"]
type ResourceType = Literal["datasource", "dataset", "file", "asset", "screen"]
type Permission = Literal["read", "write", "publish"]
type Identifier = Annotated[str, StringConstraints(min_length=1, max_length=36)]


class UserCreate(ContractModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    password: str = Field(min_length=10, max_length=1024)
    role: Role = "viewer"


class UserPatch(ContractModel):
    role: Role | None = None
    active: StrictBool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=1024)

    @model_validator(mode="after")
    def nonempty(self) -> Self:
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Provide at least one non-null account change.")
        return self


class UserResponse(ContractModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: str
    username: str
    role: Role
    active: bool
    created_at: datetime
    updated_at: datetime


class GrantRequest(ContractModel):
    resource_type: ResourceType
    resource_id: Identifier
    user_id: Identifier
    permission: Permission


class AuditResponse(ContractModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: str
    actor_id: str
    action: str
    resource_type: str | None
    resource_id: str | None
    subject_id: str | None
    request_id: str
    created_at: datetime


class SpeechProviderOption(ContractModel):
    id: str
    name: str
    language: str
    default_voice: str


class ResourceAccessResponse(ContractModel):
    read: bool
    write: bool
    publish: bool
    manage: bool
