"""Add file asset metadata and nullable dataset source."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_file_datasets"
down_revision: str | None = "0006_embed_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "file_asset",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("fields_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("dataset") as batch_op:
        batch_op.alter_column(
            "data_source_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("dataset") as batch_op:
        batch_op.alter_column(
            "data_source_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
    op.drop_table("file_asset")
