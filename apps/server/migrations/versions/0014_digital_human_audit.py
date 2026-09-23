"""Record non-sensitive digital human configuration and runtime audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_digital_human_audit"
down_revision: str | None = "0013_digital_human_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "digital_human_audit",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_digital_human_audit_created_at", "digital_human_audit", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_digital_human_audit_created_at", table_name="digital_human_audit")
    op.drop_table("digital_human_audit")
