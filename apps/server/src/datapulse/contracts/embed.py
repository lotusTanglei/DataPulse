from datetime import datetime, timedelta
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, RootModel, field_validator, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr


class EmbedTicketClaims(ContractModel):
    schema_version: Literal[1] = 1
    issuer: NonBlankStr = "datapulse"
    audience: NonBlankStr = "datapulse-embed"
    ticket_id: NonBlankStr
    screen_id: NonBlankStr
    allowed_origin: NonBlankStr
    issued_at: datetime
    expires_at: datetime
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    mutable_parameters: tuple[NonBlankStr, ...] = Field(default_factory=tuple)

    @field_validator("allowed_origin")
    @classmethod
    def validate_allowed_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if value == "*" or not parsed.hostname:
            raise ValueError("allowed_origin must identify one host")
        is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (is_local and parsed.scheme == "http"):
            raise ValueError("allowed_origin must use HTTPS except for local development")
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError(
                "allowed_origin must not contain credentials, path, query, or fragment"
            )
        return value

    @model_validator(mode="after")
    def validate_claims(self) -> Self:
        lifetime = self.expires_at - self.issued_at
        if lifetime <= timedelta(0):
            raise ValueError("expires_at must be after issued_at")
        if lifetime > timedelta(hours=8):
            raise ValueError("embed ticket lifetime cannot exceed eight hours")
        if len(self.mutable_parameters) != len(set(self.mutable_parameters)):
            raise ValueError("mutable_parameters must be unique")
        return self


class Message(ContractModel):
    instance_id: NonBlankStr


class ReadyMessage(Message):
    type: Literal["ready"]
    protocol_version: Literal[1] = 1


class RefreshMessage(Message):
    type: Literal["refresh"]


class SetParametersMessage(Message):
    type: Literal["setParameters"]
    request_id: NonBlankStr
    parameters: dict[str, JsonValue]


class GetParametersMessage(Message):
    type: Literal["getParameters"]
    request_id: NonBlankStr


class ParametersMessage(Message):
    type: Literal["parameters"]
    request_id: NonBlankStr
    parameters: dict[str, JsonValue]


class FullscreenMessage(Message):
    type: Literal["fullscreen"]
    request_id: NonBlankStr
    enabled: bool


class AckMessage(Message):
    type: Literal["ack"]
    request_id: NonBlankStr


class ErrorMessage(Message):
    type: Literal["error"]
    request_id: str | None = None
    code: NonBlankStr
    message: NonBlankStr


EmbedMessage = Annotated[
    ReadyMessage
    | RefreshMessage
    | SetParametersMessage
    | GetParametersMessage
    | ParametersMessage
    | FullscreenMessage
    | AckMessage
    | ErrorMessage,
    Field(discriminator="type"),
]


class EmbedMessageEnvelope(RootModel[EmbedMessage]):
    pass
