"""Add media metadata and immutable screen asset versions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_screen_asset_media"
down_revision: str | None = "0008_screen_access_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("screen_asset") as batch:
        batch.add_column(sa.Column("name", sa.String(255), nullable=False, server_default=""))
        batch.add_column(
            sa.Column("original_name", sa.String(255), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("family_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("media_json", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("thumbnail_path", sa.Text(), nullable=True))
        batch.add_column(sa.Column("license_note", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("uploaded_by", sa.String(255), nullable=False, server_default="")
        )
    assets = sa.table(
        "screen_asset",
        sa.column("id"),
        sa.column("family_id"),
        sa.column("name"),
        sa.column("original_name"),
    )
    op.execute(
        assets.update().values(family_id=assets.c.id, name=assets.c.id, original_name=assets.c.id)
    )
    with op.batch_alter_table("screen_asset") as batch:
        batch.alter_column("family_id", existing_type=sa.String(36), nullable=False)
        batch.create_unique_constraint("uq_screen_asset_version", ["family_id", "version"])
        batch.create_index("ix_screen_asset_sha256", ["sha256"])


def downgrade() -> None:
    with op.batch_alter_table("screen_asset") as batch:
        batch.drop_index("ix_screen_asset_sha256")
        batch.drop_constraint("uq_screen_asset_version", type_="unique")
        for name in [
            "uploaded_by",
            "license_expires_at",
            "license_note",
            "thumbnail_path",
            "media_json",
            "version",
            "family_id",
            "original_name",
            "name",
        ]:
            batch.drop_column(name)
