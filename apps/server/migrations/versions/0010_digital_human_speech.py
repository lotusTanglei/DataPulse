"""Persist digital human providers, speech plans, tasks and usage."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_digital_human_speech"
down_revision: str | None = "0009_screen_asset_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "digital_human_provider",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("provider_type", sa.String(32), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("secret_envelope", sa.Text(), nullable=True),
        sa.Column("default_voice", sa.String(120), nullable=False, server_default=""),
        sa.Column("language", sa.String(32), nullable=False, server_default="zh-CN"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_digital_human_provider_name"),
    )
    op.create_table(
        "speech_plan",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("screen_id", sa.String(36), nullable=False),
        sa.Column("component_id", sa.String(128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("provider_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("voice", sa.String(120), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_speech_plan_screen_id", "speech_plan", ["screen_id"])
    op.create_index("ix_speech_plan_content_hash", "speech_plan", ["content_hash"])
    op.create_table(
        "speech_task",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("provider_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("asset_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_speech_task_plan_id", "speech_task", ["plan_id"])
    op.create_index("ix_speech_task_status", "speech_task", ["status"])
    op.create_table(
        "digital_human_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("succeeded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cached_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "period_start", "provider_id", name="uq_digital_human_usage_period_provider"
        ),
    )
    op.create_index("ix_digital_human_usage_period_start", "digital_human_usage", ["period_start"])


def downgrade() -> None:
    op.drop_index("ix_digital_human_usage_period_start", table_name="digital_human_usage")
    op.drop_table("digital_human_usage")
    op.drop_index("ix_speech_task_status", table_name="speech_task")
    op.drop_index("ix_speech_task_plan_id", table_name="speech_task")
    op.drop_table("speech_task")
    op.drop_index("ix_speech_plan_content_hash", table_name="speech_plan")
    op.drop_index("ix_speech_plan_screen_id", table_name="speech_plan")
    op.drop_table("speech_plan")
    op.drop_table("digital_human_provider")
