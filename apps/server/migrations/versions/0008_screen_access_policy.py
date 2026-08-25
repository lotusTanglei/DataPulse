"""Add per-screen domain and IP access rules."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_screen_access_policy"
down_revision: str | None = "0007_file_datasets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("screen") as batch_op:
        batch_op.add_column(
            sa.Column(
                "access_policy_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.alter_column("access_policy_json", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("screen") as batch_op:
        batch_op.drop_column("access_policy_json")
