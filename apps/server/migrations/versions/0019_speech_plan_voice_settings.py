"""Persist TTS voice settings in speech plans."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_speech_plan_voice_settings"
down_revision: str | None = "0018_speech_metrics_timing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("speech_plan") as batch:
        batch.add_column(sa.Column("rate", sa.Float(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("pitch", sa.Float(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("volume", sa.Float(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("speech_plan") as batch:
        batch.drop_column("volume")
        batch.drop_column("pitch")
        batch.drop_column("rate")
