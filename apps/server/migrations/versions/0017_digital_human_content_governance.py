"""Add digital human content governance settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_digital_human_content_governance"
down_revision: str | None = "0016_speech_task_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("digital_human_settings") as batch:
        batch.add_column(
            sa.Column("forbidden_words", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(
            sa.Column("sensitive_patterns", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(
            sa.Column(
                "manual_review_required", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("digital_human_settings") as batch:
        batch.drop_column("manual_review_required")
        batch.drop_column("sensitive_patterns")
        batch.drop_column("forbidden_words")
