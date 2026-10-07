"""The first name needs a setup code from the server log.

Revision ID: 0014
Revises: 0013
Created: 2026-10-07 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.add_column(sa.Column("einrichtung", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.drop_column("einrichtung")
