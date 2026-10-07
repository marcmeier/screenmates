"""The time zone becomes a setting; databases from before keep Europe/Berlin.

Revision ID: 0015
Revises: 0014
Created: 2026-10-07 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.add_column(sa.Column("zeitzone", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""))
    # Until now every date was German time. A fresh database (no names yet): its first admin decides.
    op.execute("UPDATE appmeta SET zeitzone = 'Europe/Berlin' WHERE EXISTS (SELECT 1 FROM user)")


def downgrade() -> None:
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.drop_column("zeitzone")
