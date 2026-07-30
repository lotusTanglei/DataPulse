"""Require unique dataset names."""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_dataset_name_unique"
down_revision: str | None = "0001_datasource_studio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("dataset") as batch_op:
        batch_op.create_unique_constraint("uq_dataset_name", ["name"])


def downgrade() -> None:
    with op.batch_alter_table("dataset") as batch_op:
        batch_op.drop_constraint("uq_dataset_name", type_="unique")
