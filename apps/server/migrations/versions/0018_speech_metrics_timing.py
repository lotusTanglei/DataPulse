"""Persist speech synthesis timing metrics for cross-process aggregation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_speech_metrics_timing"
down_revision: str | None = "0017_digital_human_content_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("digital_human_usage") as batch:
        batch.add_column(
            sa.Column("synthesis_attempts", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("synthesis_failures", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("synthesis_total_ms", sa.Float(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("digital_human_usage") as batch:
        batch.drop_column("synthesis_total_ms")
        batch.drop_column("synthesis_failures")
        batch.drop_column("synthesis_attempts")
