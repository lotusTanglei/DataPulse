"""Add local identities, resource ownership, grants and redacted audit."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_identity"
down_revision: str | None = "0019_speech_plan_voice_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("admin_account") as batch:
        batch.add_column(sa.Column("role", sa.String(16), nullable=False, server_default="admin"))
        batch.add_column(
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true())
        )
    op.create_table(
        "resource_ownership",
        sa.Column("resource_type", sa.String(16), primary_key=True),
        sa.Column("resource_id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("admin_account.id"), nullable=False),
    )
    op.create_index("ix_resource_ownership_owner_id", "resource_ownership", ["owner_id"])
    op.create_table(
        "resource_grant",
        sa.Column("resource_type", sa.String(16), primary_key=True),
        sa.Column("resource_id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("admin_account.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("permission", sa.String(16), nullable=False),
    )
    op.create_table(
        "identity_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("resource_type", sa.String(16), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    connection = op.get_bind()
    owner = connection.scalar(sa.text("SELECT id FROM admin_account ORDER BY created_at LIMIT 1"))
    if owner is not None:
        for kind, table in [
            ("datasource", "data_source"),
            ("dataset", "dataset"),
            ("file", "file_asset"),
            ("asset", "screen_asset"),
            ("screen", "screen"),
        ]:
            connection.execute(
                sa.text(
                    "INSERT INTO resource_ownership (resource_type, resource_id, owner_id) "
                    f"SELECT :kind, id, :owner FROM {table}"
                ),
                {"kind": kind, "owner": owner},
            )


def downgrade() -> None:
    op.drop_table("identity_audit")
    op.drop_table("resource_grant")
    op.drop_table("resource_ownership")
    with op.batch_alter_table("admin_account") as batch:
        batch.drop_column("active")
        batch.drop_column("role")
