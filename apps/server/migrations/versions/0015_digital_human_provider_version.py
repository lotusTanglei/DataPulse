"""Include provider versions in speech cache identity."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_digital_human_provider_version"
down_revision: str | None = "0014_digital_human_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("digital_human_provider") as batch:
        batch.add_column(
            sa.Column(
                "provider_version", sa.String(length=120), nullable=False, server_default="v1"
            )
        )
    with op.batch_alter_table("speech_plan") as batch:
        batch.add_column(
            sa.Column(
                "provider_version", sa.String(length=120), nullable=False, server_default="v1"
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("speech_plan") as batch:
        batch.drop_column("provider_version")
    with op.batch_alter_table("digital_human_provider") as batch:
        batch.drop_column("provider_version")
