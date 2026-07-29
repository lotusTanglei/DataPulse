from datetime import datetime
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, RootModel, field_validator, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr


class EmbedTicketClaims(ContractModel):
    schema_version: Literal[1] = 1
    issuer: NonBlankStr = "datapulse"
    audience: NonBlankStr = "datapulse-embed"
    dashboard_id: NonBlankStr
    published_version_id: NonBlankStr
    allowed_origin: NonBlankStr
    issued_at: datetime
    expires_at: datetime
    ai_enabled: bool = False
    parameters: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("allowed_origin")
    @classmethod
    def validate_allowed_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if value == "*" or not parsed.hostname:
            raise ValueError("allowed_origin must identify one host")
        is_local = parsed.hostname in {"localhost", "127.0.0.1"}
        if parsed.scheme != "https" and not (is_local and parsed.scheme == "http"):
            raise ValueError("allowed_origin must use HTTPS except for local development")
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError(
                "allowed_origin must not contain credentials, path, query, or fragment"
            )
        return value

    @model_validator(mode="after")
    def validate_expiration(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        return self


class ReadyMessage(ContractModel):
    type: Literal["ready"]


class RefreshMessage(ContractModel):
    type: Literal["refresh"]


class SetParametersMessage(ContractModel):
    type: Literal["setParameters"]
    request_id: NonBlankStr
    parameters: dict[str, JsonValue]


class GetParametersMessage(ContractModel):
    type: Literal["getParameters"]
    request_id: NonBlankStr


class FullscreenMessage(ContractModel):
    type: Literal["fullscreen"]
    request_id: NonBlankStr
    enabled: bool


class ExportImageMessage(ContractModel):
    type: Literal["exportImage"]
    request_id: NonBlankStr
    format: Literal["png", "jpeg"] = "png"


class ErrorMessage(ContractModel):
    type: Literal["error"]
    request_id: str | None = None
    code: NonBlankStr
    message: NonBlankStr


class AiQuestionMessage(ContractModel):
    type: Literal["aiQuestion"]
    request_id: NonBlankStr
    question: NonBlankStr


EmbedMessage = Annotated[
    ReadyMessage
    | RefreshMessage
    | SetParametersMessage
    | GetParametersMessage
    | FullscreenMessage
    | ExportImageMessage
    | ErrorMessage
    | AiQuestionMessage,
    Field(discriminator="type"),
]


class EmbedMessageEnvelope(RootModel[EmbedMessage]):
    pass
