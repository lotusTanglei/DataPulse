"""Persist global digital human settings and server-side speech quotas."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_digital_human_settings"
down_revision: str | None = "0010_digital_human_speech"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "digital_human_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("default_subtitles", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_speech_seconds", sa.Float(), nullable=False, server_default="30"),
        sa.Column("cooldown_seconds", sa.Float(), nullable=False, server_default="5"),
        sa.Column("daily_task_limit", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column(
            "daily_audio_seconds_limit", sa.Float(), nullable=False, server_default="36000"
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text(
            "INSERT INTO digital_human_settings "
            "(id, enabled, default_muted, default_subtitles, max_speech_seconds, "
            "cooldown_seconds, daily_task_limit, daily_audio_seconds_limit, updated_at) "
            "VALUES (1, 1, 0, 1, 30, 5, 1000, 36000, CURRENT_TIMESTAMP)"
        )
    )


def downgrade() -> None:
    op.drop_table("digital_human_settings")
