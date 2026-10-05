"""Zugangsfrage, Admins pro Person und Namensanträge statt Host-Film.

- user: is_admin, freigegeben (bestehende Namen bleiben freigegeben)
- session: zugang statt is_host; wer schon angemeldet ist, behält den Zugang
- zugang: die Zugangsfrage (eine Zeile, id=1)
- hoststate fällt weg: Admin ist jetzt ein Recht einer Person

Wer Admin wird, legt die Migration nicht fest: `python -m app.cli admin "<Name>"`.

Revision ID: 0003
Revises: 0002
Created: 2026-10-05 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zugang",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("frage", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=True),
        sa.Column("titel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("geaendert", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zugang")),
    )
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("freigegeben", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    with op.batch_alter_table("session", schema=None) as batch_op:
        batch_op.add_column(sa.Column("zugang", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    # Browsers that are logged in today stay inside once the door is set up.
    op.execute("UPDATE session SET zugang = 1 WHERE user_id IS NOT NULL")
    with op.batch_alter_table("session", schema=None) as batch_op:
        batch_op.drop_column("is_host")
    op.drop_table("hoststate")


def downgrade() -> None:
    op.create_table(
        "hoststate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hoststate")),
    )
    with op.batch_alter_table("session", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_host", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.drop_column("zugang")
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("freigegeben")
        batch_op.drop_column("is_admin")
    op.drop_table("zugang")
