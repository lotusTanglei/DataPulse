from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from datapulse.metadata.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid4())


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime values must be timezone-aware.")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class QueryRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class SystemState(Base):
    __tablename__ = "system_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setup_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    setup_code_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class AdminAccount(Base):
    __tablename__ = "admin_account"
    __table_args__ = (UniqueConstraint("username", name="uq_admin_account_username"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="admin", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_changed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )


class AdminSession(Base):
    __tablename__ = "admin_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[str] = mapped_column(
        ForeignKey("admin_account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)


class DataSourceRecord(Base):
    __tablename__ = "data_source"
    __table_args__ = (UniqueConstraint("name", name="uq_data_source_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    secret_envelope: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )


class DatasetRecord(Base):
    __tablename__ = "dataset"
    __table_args__ = (UniqueConstraint("name", name="uq_dataset_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("data_source.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )


class FileAssetRecord(Base):
    __tablename__ = "file_asset"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fields_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)


class ScreenRecord(Base):
    __tablename__ = "screen"
    __table_args__ = (UniqueConstraint("name", name="uq_screen_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    draft_document: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_document: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    access_policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )


class DisplayAccessRecord(Base):
    __tablename__ = "display_access"

    screen_id: Mapped[str] = mapped_column(
        ForeignKey("screen.id", ondelete="CASCADE"),
        primary_key=True,
    )
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class EmbedAccessRecord(Base):
    __tablename__ = "embed_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ScreenAssetRecord(Base):
    __tablename__ = "screen_asset"
    __table_args__ = (UniqueConstraint("family_id", "version", name="uq_screen_asset_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    media_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    license_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)


class DigitalHumanProviderRecord(Base):
    __tablename__ = "digital_human_provider"
    __table_args__ = (UniqueConstraint("name", name="uq_digital_human_provider_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    secret_envelope: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_voice: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="zh-CN", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cost_per_minute: Mapped[float] = mapped_column(default=0, nullable=False)
    provider_version: Mapped[str] = mapped_column(String(120), default="v1", nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    circuit_open_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )


class DigitalHumanSettingsRecord(Base):
    __tablename__ = "digital_human_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_subtitles: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_speech_seconds: Mapped[float] = mapped_column(default=30, nullable=False)
    cooldown_seconds: Mapped[float] = mapped_column(default=5, nullable=False)
    daily_task_limit: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    daily_audio_seconds_limit: Mapped[float] = mapped_column(default=36_000, nullable=False)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    ai_context_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    data_retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    forbidden_words: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    sensitive_patterns: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )


class SpeechPlanRecord(Base):
    __tablename__ = "speech_plan"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    screen_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    component_id: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    voice: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    rate: Mapped[float] = mapped_column(default=1, nullable=False)
    pitch: Mapped[float] = mapped_column(default=1, nullable=False)
    volume: Mapped[float] = mapped_column(default=1, nullable=False)
    provider_version: Mapped[str] = mapped_column(String(120), default="v1", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)


class SpeechTaskRecord(Base):
    __tablename__ = "speech_task"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="runtime", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    reserved_audio_seconds: Mapped[float] = mapped_column(default=0, nullable=False)
    quota_period: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class DigitalHumanUsageRecord(Base):
    __tablename__ = "digital_human_usage"
    __table_args__ = (
        UniqueConstraint(
            "period_start", "provider_id", name="uq_digital_human_usage_period_provider"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    period_start: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    succeeded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    generated_seconds: Mapped[float] = mapped_column(default=0, nullable=False)
    cached_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(default=0, nullable=False)
    synthesis_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    synthesis_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    synthesis_total_ms: Mapped[float] = mapped_column(default=0, nullable=False)


class DigitalHumanProviderHealthRecord(Base):
    __tablename__ = "digital_human_provider_health"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)


class DigitalHumanAuditRecord(Base):
    __tablename__ = "digital_human_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)


class QueryRunRecord(Base):
    __tablename__ = "query_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    data_source_id: Mapped[str] = mapped_column(
        ForeignKey("data_source.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset.id", ondelete="SET NULL"), nullable=True, index=True
    )
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=QueryRunStatus.RUNNING.value, nullable=False
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truncated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class ResourceOwnershipRecord(Base):
    __tablename__ = "resource_ownership"

    resource_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("admin_account.id"), nullable=False, index=True
    )


class ResourceGrantRecord(Base):
    __tablename__ = "resource_grant"

    resource_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("admin_account.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(String(16), nullable=False)


class IdentityAuditRecord(Base):
    __tablename__ = "identity_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
