"""Add revocable standalone display access."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_display_access"
down_revision: str | None = "0004_screen_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "display_access",
        sa.Column("screen_id", sa.String(length=36), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["screen_id"],
            ["screen.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("screen_id"),
    )


def downgrade() -> None:
    op.drop_table("display_access")
