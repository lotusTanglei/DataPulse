"""Track provider health history, circuit state, and estimated speech cost."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_digital_human_health_cost"
down_revision: str | None = "0011_digital_human_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("digital_human_provider") as batch:
        batch.add_column(
            sa.Column("cost_per_minute", sa.Float(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("circuit_open_until", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_latency_ms", sa.Integer(), nullable=True))
    with op.batch_alter_table("digital_human_usage") as batch:
        batch.add_column(
            sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0")
        )
    op.create_table(
        "digital_human_provider_health",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_digital_human_provider_health_provider_id",
        "digital_human_provider_health",
        ["provider_id"],
    )
    op.create_index(
        "ix_digital_human_provider_health_checked_at",
        "digital_human_provider_health",
        ["checked_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_digital_human_provider_health_checked_at",
        table_name="digital_human_provider_health",
    )
    op.drop_index(
        "ix_digital_human_provider_health_provider_id",
        table_name="digital_human_provider_health",
    )
    op.drop_table("digital_human_provider_health")
    with op.batch_alter_table("digital_human_usage") as batch:
        batch.drop_column("estimated_cost")
    with op.batch_alter_table("digital_human_provider") as batch:
        batch.drop_column("last_latency_ms")
        batch.drop_column("circuit_open_until")
        batch.drop_column("consecutive_failures")
        batch.drop_column("cost_per_minute")
