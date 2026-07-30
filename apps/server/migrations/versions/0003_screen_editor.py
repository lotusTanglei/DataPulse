"""Add screen draft persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_screen_editor"
down_revision: str | None = "0002_dataset_name_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "screen",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("draft_document", sa.JSON(), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False),
        sa.Column("published_document", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_screen_name"),
    )


def downgrade() -> None:
    op.drop_table("screen")
