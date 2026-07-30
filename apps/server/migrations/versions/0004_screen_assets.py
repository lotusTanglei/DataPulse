"""Add controlled screen asset storage."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_screen_assets"
down_revision: str | None = "0003_screen_editor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "screen_asset",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("screen_asset")
