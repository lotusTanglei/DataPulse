"""Add AI controls and speech data retention settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_digital_human_governance"
down_revision: str | None = "0012_digital_human_health_cost"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("digital_human_settings") as batch:
        batch.add_column(
            sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column("ai_model", sa.String(length=120), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("ai_context_limit", sa.Integer(), nullable=False, server_default="100")
        )
        batch.add_column(
            sa.Column("data_retention_days", sa.Integer(), nullable=False, server_default="30")
        )


def downgrade() -> None:
    with op.batch_alter_table("digital_human_settings") as batch:
        batch.drop_column("data_retention_days")
        batch.drop_column("ai_context_limit")
        batch.drop_column("ai_model")
        batch.drop_column("ai_enabled")
