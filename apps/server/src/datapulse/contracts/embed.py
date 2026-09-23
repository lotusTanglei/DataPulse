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
    capabilities: tuple[NonBlankStr, ...] = Field(default_factory=tuple)


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


SpeechState = Literal[
    "disabled",
    "idle",
    "loading_data",
    "ready",
    "queued",
    "preparing_media",
    "speaking",
    "paused",
    "muted",
    "waiting_gesture",
    "fallback",
    "error",
]


class DigitalHumanCommand(ContractModel):
    component_id: NonBlankStr
    action: Literal["play", "pause", "stop", "speak", "getStatus", "mute", "setVolume"]
    enabled: bool | None = Field(default=None, strict=True)
    volume: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False, strict=True)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        if (self.action == "mute") != (self.enabled is not None):
            raise ValueError("Only mute commands require enabled.")
        if (self.action == "setVolume") != (self.volume is not None):
            raise ValueError("Only volume commands require volume.")
        return self


class DigitalHumanMessage(Message):
    type: Literal["digitalHuman"]
    request_id: NonBlankStr
    command: DigitalHumanCommand


class DigitalHumanState(ContractModel):
    component_id: NonBlankStr
    status: SpeechState
    code: str | None
    muted: bool
    volume: float = Field(ge=0, le=1, allow_inf_nan=False)


class DigitalHumanStatusMessage(Message):
    type: Literal["digitalHumanStatus"]
    request_id: NonBlankStr
    state: DigitalHumanState


class DigitalHumanEvent(ContractModel):
    name: Literal[
        "digitalHumanReady",
        "statusChange",
        "speechStart",
        "speechEnd",
        "speechError",
        "fallback",
        "userGestureRequired",
        "subtitleCue",
    ] = "statusChange"
    outcome: Literal["completed", "stopped", "cancelled"] | None = None
    component_id: NonBlankStr
    status: SpeechState
    task_id: str | None
    source: Literal[
        "initial",
        "manual",
        "interval",
        "data_change",
        "ranking_change",
        "status_change",
        "threshold",
        "parameter",
        "host",
    ]
    code: str | None
    request_id: str
    timestamp: float = Field(ge=0, allow_inf_nan=False)
    cue_index: int | None = Field(default=None, ge=0, strict=True)
    cue_text: str | None = None
    cue_start: float | None = Field(default=None, ge=0, allow_inf_nan=False, strict=True)
    cue_end: float | None = Field(default=None, ge=0, allow_inf_nan=False, strict=True)

    @model_validator(mode="after")
    def validate_subtitle_cue(self) -> Self:
        cue_values = (self.cue_index, self.cue_text, self.cue_start, self.cue_end)
        has_any_cue = any(value is not None for value in cue_values)
        if self.name == "subtitleCue" or has_any_cue:
            if any(value is None for value in cue_values):
                raise ValueError(
                    "subtitleCue events require cue_index, cue_text, cue_start, and cue_end"
                )
            if self.cue_end <= self.cue_start:
                raise ValueError("cue_end must be after cue_start")
        return self


class DigitalHumanEventMessage(Message):
    type: Literal["digitalHumanEvent"]
    event: DigitalHumanEvent


EmbedMessage = Annotated[
    ReadyMessage
    | RefreshMessage
    | SetParametersMessage
    | GetParametersMessage
    | ParametersMessage
    | FullscreenMessage
    | AckMessage
    | DigitalHumanMessage
    | DigitalHumanStatusMessage
    | DigitalHumanEventMessage
    | ErrorMessage,
    Field(discriminator="type"),
]


class EmbedMessageEnvelope(RootModel[EmbedMessage]):
    pass
