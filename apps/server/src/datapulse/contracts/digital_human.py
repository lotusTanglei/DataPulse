from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, StringConstraints, field_validator, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.screen_asset import SubtitleCue
from datapulse.contracts.speech_template import parse_speech_template, sensitive_speech_field

AssetId = Annotated[str, StringConstraints(pattern=r"^[\w-]{0,128}$")]
VariableName = Annotated[str, StringConstraints(pattern=r"^[\w.-]{1,128}$")]
ColorHex = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")]


class DigitalHumanVariable(ContractModel):
    name: VariableName
    component_id: NonBlankStr
    field: NonBlankStr
    row: int = Field(default=0, ge=0, le=499)
    unit: str = Field(default="", max_length=24)
    enum_labels: dict[str, str] = Field(default_factory=dict, max_length=50)

    @model_validator(mode="after")
    def validate_field(self) -> Self:
        if sensitive_speech_field(self.field) or sensitive_speech_field(self.name):
            raise ValueError("Sensitive fields cannot be used for speech.")
        parse_speech_template("{{" + self.name + "}}")
        if any(len(value) > 120 for value in self.enum_labels.values()):
            raise ValueError("Speech enum labels cannot exceed 120 characters.")
        return self


class DigitalHumanBinding(ContractModel):
    source: Literal["components"] = "components"
    variables: tuple[DigitalHumanVariable, ...] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        names = [item.name for item in self.variables]
        if len(names) != len(set(names)):
            raise ValueError("Speech variable names must be unique.")
        return self


class DigitalHumanCondition(ContractModel):
    variable: VariableName
    operator: Literal["gt", "gte", "lt", "lte", "eq", "neq", "exists"] = "gt"
    value: JsonValue = None

    @model_validator(mode="after")
    def validate_value(self) -> Self:
        if isinstance(self.value, (list, dict)):
            raise ValueError("Speech conditions only support scalar values.")
        if self.operator == "exists" and self.value is not None:
            raise ValueError("The exists condition does not accept a value.")
        if self.operator != "exists" and self.value is None:
            raise ValueError("A speech condition value is required.")
        return self


class DigitalHumanTrigger(ContractModel):
    kind: Literal[
        "initial",
        "manual",
        "interval",
        "data_change",
        "ranking_change",
        "status_change",
        "threshold",
        "parameter",
    ] = "data_change"
    interval_seconds: int | None = Field(default=None, ge=10, le=86400)
    cooldown_seconds: int = Field(default=30, ge=1, le=86400)
    min_change: float = Field(default=0, ge=0, allow_inf_nan=False)
    variable: VariableName | None = None
    threshold: float | None = Field(default=None, allow_inf_nan=False)
    direction: Literal["above", "below"] = "above"
    edge: Literal["enter", "recover", "both"] = "enter"
    parameter: NonBlankStr | None = None
    include_host: bool = True
    conditions: tuple[DigitalHumanCondition, ...] = Field(default_factory=tuple, max_length=20)
    condition_mode: Literal["all", "any"] = "all"
    priority: int = Field(default=0, ge=-100, le=100)
    debounce_seconds: int = Field(default=0, ge=0, le=3600)
    window_start: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    window_end: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def validate_trigger(self) -> Self:
        if self.kind == "interval" and self.interval_seconds is None:
            raise ValueError("interval_seconds is required for interval triggers")
        if self.kind != "interval" and self.interval_seconds is not None:
            raise ValueError("interval_seconds is only valid for interval triggers")
        if self.kind == "threshold" and not self.conditions and (
            self.threshold is None or self.variable is None
        ):
            raise ValueError("threshold and variable are required for threshold triggers")
        if self.kind in {"ranking_change", "status_change"} and self.variable is None:
            raise ValueError("variable is required for ranking and status change triggers")
        if self.kind != "threshold" and self.conditions:
            raise ValueError("conditions are only valid for threshold triggers")
        if self.kind == "parameter" and self.parameter is None:
            raise ValueError("parameter is required for parameter triggers")
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError("Both trigger window start and end are required.")
        return self


class DigitalHumanAction(ContractModel):
    id: Annotated[str, StringConstraints(pattern=r"^[\w.-]{1,64}$")]
    kind: Literal["nod", "wave", "emphasis"] = "emphasis"
    asset_id: Annotated[str, StringConstraints(pattern=r"^[\w-]{1,128}$")]
    asset_kind: Literal["image", "video"] = "image"
    priority: int = Field(default=0, ge=-100, le=100)
    duration_ms: int = Field(default=1200, ge=100, le=10_000)
    conditions: tuple[DigitalHumanCondition, ...] = Field(default_factory=tuple, max_length=20)
    condition_mode: Literal["all", "any"] = "all"


class SpeechScriptSegment(ContractModel):
    kind: Literal["paragraph", "pause", "emphasis"] = "paragraph"
    text: str = Field(default="", max_length=4000)
    duration_ms: int = Field(default=500, ge=100, le=10_000)

    @model_validator(mode="after")
    def validate_segment(self) -> Self:
        if self.kind in {"paragraph", "emphasis"} and not self.text.strip():
            raise ValueError("Text is required for paragraph and emphasis segments.")
        if self.kind == "pause" and self.text:
            raise ValueError("Pause segments cannot contain text.")
        return self


class SpeechRecording(ContractModel):
    asset_id: Annotated[str, StringConstraints(pattern=r"^[\w-]{1,128}$")]
    sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    transcript: str = Field(min_length=1, max_length=4000)
    duration_seconds: float = Field(gt=0, le=86400, allow_inf_nan=False)
    priority: int = Field(default=0, ge=-100, le=100)
    subtitle_asset_id: AssetId = ""
    subtitle_sha256: str = Field(default="", pattern=r"^(?:[a-f0-9]{64})?$")
    cues: tuple[SubtitleCue, ...] = Field(default_factory=tuple, max_length=500)
    conditions: tuple[DigitalHumanCondition, ...] = Field(default_factory=tuple, max_length=20)
    condition_mode: Literal["all", "any"] = "all"

    @model_validator(mode="after")
    def valid_recording(self) -> Self:
        if not self.transcript.strip():
            raise ValueError("A recording requires a confirmed transcript.")
        if bool(self.subtitle_asset_id) != bool(self.subtitle_sha256):
            raise ValueError("A subtitle reference requires its content hash.")
        if self.subtitle_asset_id and not self.cues:
            raise ValueError("A subtitle reference requires its validated cues.")
        previous_end = 0.0
        for cue in self.cues:
            if cue.start < previous_end or cue.end <= cue.start or cue.end > self.duration_seconds:
                raise ValueError("Subtitle cues must be ordered and within the recording duration.")
            previous_end = cue.end
        if self.cues:

            def normalize(text: str) -> str:
                return " ".join(text.split())

            versions = {
                normalize(separator.join(cue.text for cue in self.cues)) for separator in ("", " ")
            }
            if normalize(self.transcript) not in versions:
                raise ValueError("Subtitle text must match the confirmed transcript.")
        return self


class DigitalHumanSpec(ContractModel):
    schema_version: Literal[1] = 1
    enabled: bool = True
    avatar_asset_id: AssetId = ""
    speaking_asset_id: AssetId = ""
    audio_asset_id: AssetId = ""
    speech_source: Literal["auto", "browser", "audio", "video"] = "auto"
    recording: SpeechRecording | None = None
    recordings: tuple[SpeechRecording, ...] = Field(default_factory=tuple, max_length=20)
    speech_segments: tuple[SpeechScriptSegment, ...] = Field(default_factory=tuple, max_length=50)
    actions: tuple[DigitalHumanAction, ...] = Field(default_factory=tuple, max_length=8)
    avatar_kind: Literal["image", "video"] = "image"
    speaking_kind: Literal["image", "video"] = "image"
    fit: Literal["contain", "cover", "none"] = "contain"
    mirror: bool = False
    name: str = Field(default="DataPulse 数字人", min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)
    show_identity: bool = True
    show_status: bool = True
    show_controls: bool = True
    animation: bool = True
    speech_template: str = Field(default="数据播报：{{value}}", min_length=1, max_length=4000)
    empty_text: str = Field(default="暂无数据", max_length=500)
    missing_text: str = Field(default="字段不可用", max_length=500)
    error_text: str = Field(default="数据暂不可播报", max_length=500)
    stale_text: str = Field(default="数据已过期", max_length=500)
    stale_after_seconds: int = Field(default=300, ge=10, le=86400)
    language: str = Field(default="zh-CN", pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
    timezone: str = "Asia/Shanghai"
    rate: float = Field(default=1, ge=0.5, le=2, allow_inf_nan=False)
    pitch: float = Field(default=1, ge=0, le=2, allow_inf_nan=False)
    volume: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    auto_play: bool = True
    voice_enabled: bool = True
    subtitle_enabled: bool = True
    subtitle_position: Literal["top", "bottom"] = "bottom"
    subtitle_color: ColorHex = "#FFFFFF"
    subtitle_background: ColorHex = "#000000B8"
    subtitle_scroll: Literal["wrap", "scroll"] = "wrap"
    subtitle_font_size: int = Field(default=20, ge=12, le=80)
    subtitle_max_lines: int = Field(default=3, ge=1, le=10)
    muted: bool = True
    trigger: DigitalHumanTrigger = Field(default_factory=DigitalHumanTrigger)
    queue_policy: Literal["queue", "merge", "drop_old", "interrupt"] = "merge"
    max_duration_seconds: int = Field(default=30, ge=1, le=300)
    max_queue_length: int = Field(default=5, ge=1, le=20)
    task_ttl_seconds: int = Field(default=60, ge=1, le=3600)
    daily_max_count: int = Field(default=1000, ge=1, le=10000)
    daily_max_seconds: int = Field(default=7200, ge=1, le=86400)
    quiet_start: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    quiet_end: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    quiet_mode: Literal["mute", "delay", "subtitle"] = "mute"

    @field_validator("speech_template")
    @classmethod
    def valid_template(cls, value: str) -> str:
        parse_speech_template(value)
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Unknown speech timezone.") from error
        return value

    @model_validator(mode="after")
    def quiet_hours(self) -> Self:
        if (self.quiet_start is None) != (self.quiet_end is None):
            raise ValueError("Both quiet start and quiet end are required.")
        recording_ids = [recording.asset_id for recording in self.recordings]
        if len(recording_ids) != len(set(recording_ids)):
            raise ValueError("Each prerecorded speech asset may only appear once in a mapping.")
        if self.recording and self.recording.asset_id in recording_ids:
            raise ValueError("The legacy recording cannot duplicate a mapped recording.")
        if sum(len(segment.text) for segment in self.speech_segments) > 4000:
            raise ValueError("Speech script text must not exceed 4000 characters.")
        if self.speech_segments and not any(
            segment.kind != "pause" for segment in self.speech_segments
        ):
            raise ValueError("A speech script must contain at least one text segment.")
        action_ids = [action.id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("Each digital human action must have a unique id.")
        if self._contrast_ratio(self.subtitle_color, self.subtitle_background) < 4.5:
            raise ValueError("Subtitle colors must meet a 4.5:1 contrast ratio.")
        return self

    @staticmethod
    def _contrast_ratio(foreground: str, background: str) -> float:
        def luminance(value: str) -> float:
            channels = [int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        first, second = luminance(foreground), luminance(background)
        lighter, darker = max(first, second), min(first, second)
        return (lighter + 0.05) / (darker + 0.05)
