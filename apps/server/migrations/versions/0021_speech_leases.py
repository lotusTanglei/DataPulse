"""Persist speech worker leases and audio capacity reservations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_speech_leases"
down_revision: str | None = "0020_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("speech_task") as batch:
        batch.add_column(sa.Column("lease_owner", sa.String(36), nullable=True))
        batch.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("reserved_audio_seconds", sa.Float(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("quota_period", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("speech_task") as batch:
        batch.drop_column("quota_period")
        batch.drop_column("reserved_audio_seconds")
        batch.drop_column("lease_expires_at")
        batch.drop_column("lease_owner")
