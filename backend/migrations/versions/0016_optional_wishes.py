"""Wishes & ideas becomes optional: off for new installs, on for databases already in use.

Revision ID: 0016
Revises: 0015
Created: 2026-10-07 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.add_column(sa.Column("wuensche", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE appmeta SET wuensche = 1 WHERE EXISTS (SELECT 1 FROM user)")


def downgrade() -> None:
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.drop_column("wuensche")
