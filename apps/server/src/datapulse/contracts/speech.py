import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, SecretStr, StringConstraints, field_validator, model_validator

from datapulse.contracts.common import ContractModel, NonBlankStr

ProviderType = Literal["openai_compatible", "azure", "custom"]
SpeechTaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
SpeechDraftOperation = Literal["generate", "rewrite", "shorten", "translate"]
ProviderHealthStatus = Literal[
    "unconfigured", "disabled", "healthy", "degraded", "open"
]
GovernanceWord = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
GovernancePattern = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class DigitalHumanProviderCreate(ContractModel):
    name: NonBlankStr = Field(max_length=120)
    provider_type: ProviderType
    base_url: str = Field(default="", max_length=500)
    api_key: SecretStr | None = None
    default_voice: str = Field(default="", max_length=120)
    language: str = Field(default="zh-CN", pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
    enabled: bool = True
    cost_per_minute: float = Field(default=0, ge=0, le=1_000_000)
    provider_version: str = Field(default="v1", min_length=1, max_length=120)

    @field_validator("base_url")
    @classmethod
    def valid_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Provider base URL must use HTTP or HTTPS.")
        return value


class DigitalHumanProviderUpdate(ContractModel):
    name: NonBlankStr | None = Field(default=None, max_length=120)
    provider_type: ProviderType | None = None
    base_url: str | None = Field(default=None, max_length=500)
    api_key: SecretStr | None = None
    clear_api_key: bool = False
    default_voice: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
    enabled: bool | None = None
    cost_per_minute: float | None = Field(default=None, ge=0, le=1_000_000)
    provider_version: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("base_url")
    @classmethod
    def valid_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().rstrip("/")
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Provider base URL must use HTTP or HTTPS.")
        return value


class DigitalHumanProviderResponse(ContractModel):
    id: NonBlankStr
    name: NonBlankStr
    provider_type: ProviderType
    base_url: str
    default_voice: str
    language: str
    enabled: bool
    configured: bool
    cost_per_minute: float = Field(ge=0)
    provider_version: str
    health_status: ProviderHealthStatus
    consecutive_failures: int = Field(ge=0)
    circuit_open_until: datetime | None = None
    last_checked_at: datetime | None = None
    last_latency_ms: int | None = Field(default=None, ge=0)
    last_error_code: str | None = None


class DigitalHumanProviderTestResponse(ContractModel):
    ok: bool
    latency_ms: int = Field(ge=0)
    error_code: str | None = None
    voices: tuple[str, ...] = ()


class DigitalHumanProviderHealthResponse(ContractModel):
    provider_id: str
    checked_at: datetime
    ok: bool
    latency_ms: int = Field(ge=0)
    error_code: str | None = None


class DigitalHumanCostReportRow(ContractModel):
    provider_id: str
    provider_name: str
    task_count: int = Field(ge=0)
    succeeded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    cached_count: int = Field(ge=0)
    generated_seconds: float = Field(ge=0)
    estimated_cost: float = Field(ge=0)


class DigitalHumanCostReportResponse(ContractModel):
    period_start: datetime
    period_end: datetime
    rows: tuple[DigitalHumanCostReportRow, ...]
    total_task_count: int = Field(ge=0)
    total_generated_seconds: float = Field(ge=0)
    total_estimated_cost: float = Field(ge=0)


class DigitalHumanCacheClearResponse(ContractModel):
    detached_task_count: int = Field(ge=0)
    deleted_asset_count: int = Field(ge=0)


class DigitalHumanAuditResponse(ContractModel):
    id: str
    created_at: datetime
    actor: str
    action: str
    resource_type: str
    resource_id: str
    request_id: str | None = None
    details: dict[str, str] = Field(default_factory=dict)


class SpeechPlanRequest(ContractModel):
    screen_id: NonBlankStr
    component_id: NonBlankStr
    text: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="zh-CN", pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
    provider_id: str = ""
    voice: str = ""
    rate: float = Field(default=1, ge=0.5, le=2, allow_inf_nan=False)
    pitch: float = Field(default=1, ge=0, le=2, allow_inf_nan=False)
    volume: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    data_fingerprint: str = Field(default="", max_length=128)


class SpeechPlanResponse(ContractModel):
    id: NonBlankStr
    screen_id: NonBlankStr
    component_id: NonBlankStr
    text: str
    language: str
    provider_id: str
    voice: str
    rate: float = Field(default=1, ge=0.5, le=2, allow_inf_nan=False)
    pitch: float = Field(default=1, ge=0, le=2, allow_inf_nan=False)
    volume: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    provider_version: str
    content_hash: str
    created_at: datetime


class SpeechTaskResponse(ContractModel):
    id: NonBlankStr
    plan_id: NonBlankStr
    status: SpeechTaskStatus
    provider_id: str
    asset_id: str
    error_code: str | None = None
    source: str = Field(default="runtime", min_length=1, max_length=64)
    priority: int = Field(default=0, ge=-100, le=100)
    created_at: datetime
    expires_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DigitalHumanPlaybackDiagnosticResponse(ContractModel):
    screen_id: NonBlankStr
    component_id: NonBlankStr
    task_id: NonBlankStr
    status: SpeechTaskStatus
    provider_id: str
    source: str = Field(min_length=1, max_length=64)
    asset_id: str
    error_code: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DigitalHumanUsageResponse(ContractModel):
    period_start: datetime
    task_count: int = Field(ge=0)
    succeeded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    generated_seconds: float = Field(ge=0)
    cached_count: int = Field(ge=0)
    estimated_cost: float = Field(default=0, ge=0)


class DigitalHumanMetricsResponse(ContractModel):
    collected_at: datetime
    tasks_queued: int = Field(ge=0)
    tasks_succeeded: int = Field(ge=0)
    tasks_failed: int = Field(ge=0)
    tasks_cancelled: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    synthesis_attempts: int = Field(ge=0)
    synthesis_failures: int = Field(ge=0)
    synthesis_total_ms: float = Field(ge=0)
    average_synthesis_ms: float = Field(ge=0)


class DigitalHumanSettingsResponse(ContractModel):
    enabled: bool = True
    default_muted: bool = False
    default_subtitles: bool = True
    max_speech_seconds: float = Field(default=30, gt=0, le=3600)
    cooldown_seconds: float = Field(default=5, ge=0, le=86400)
    daily_task_limit: int = Field(default=1000, ge=1, le=1_000_000)
    daily_audio_seconds_limit: float = Field(default=36_000, gt=0, le=10_000_000)
    ai_enabled: bool = True
    ai_model: str = Field(default="", max_length=120)
    ai_context_limit: int = Field(default=100, ge=1, le=10_000)
    data_retention_days: int = Field(default=30, ge=1, le=3650)
    forbidden_words: tuple[GovernanceWord, ...] = Field(default_factory=tuple, max_length=200)
    sensitive_patterns: tuple[GovernancePattern, ...] = Field(default_factory=tuple, max_length=50)
    manual_review_required: bool = False
    updated_at: datetime

    @field_validator("sensitive_patterns")
    @classmethod
    def valid_sensitive_patterns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for pattern in value:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError("Sensitive patterns must be valid regular expressions.") from error
        return value


class DigitalHumanSettingsUpdate(ContractModel):
    enabled: bool | None = None
    default_muted: bool | None = None
    default_subtitles: bool | None = None
    max_speech_seconds: float | None = Field(default=None, gt=0, le=3600)
    cooldown_seconds: float | None = Field(default=None, ge=0, le=86400)
    daily_task_limit: int | None = Field(default=None, ge=1, le=1_000_000)
    daily_audio_seconds_limit: float | None = Field(default=None, gt=0, le=10_000_000)
    ai_enabled: bool | None = None
    ai_model: str | None = Field(default=None, max_length=120)
    ai_context_limit: int | None = Field(default=None, ge=1, le=10_000)
    data_retention_days: int | None = Field(default=None, ge=1, le=3650)
    forbidden_words: tuple[GovernanceWord, ...] | None = Field(default=None, max_length=200)
    sensitive_patterns: tuple[GovernancePattern, ...] | None = Field(default=None, max_length=50)
    manual_review_required: bool | None = None

    @field_validator("sensitive_patterns")
    @classmethod
    def valid_sensitive_patterns(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if value is None:
            return value
        for pattern in value:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError("Sensitive patterns must be valid regular expressions.") from error
        return value

    @model_validator(mode="after")
    def require_change(self) -> "DigitalHumanSettingsUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one digital human setting must be updated.")
        return self


class SpeechDraftRequest(ContractModel):
    operation: SpeechDraftOperation
    source_text: str = Field(default="", max_length=4000)
    language: str = Field(default="zh-CN", pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
    tone: str = Field(default="专业、简洁", min_length=1, max_length=120)
    allowed_variables: tuple[str, ...] = Field(default=(), max_length=50)


class SpeechDraftResponse(ContractModel):
    text: str = Field(min_length=1, max_length=4000)
    warnings: tuple[str, ...] = ()
    preview_only: Literal[True] = True
