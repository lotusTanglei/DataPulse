"""Persist speech task scheduling metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_speech_task_metadata"
down_revision: str | None = "0015_digital_human_provider_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("speech_task") as batch:
        batch.add_column(sa.Column("source", sa.String(length=64), nullable=False, server_default="runtime"))
        batch.add_column(sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("speech_task") as batch:
        batch.drop_column("expires_at")
        batch.drop_column("priority")
        batch.drop_column("source")
