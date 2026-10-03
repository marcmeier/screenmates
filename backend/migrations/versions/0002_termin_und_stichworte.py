"""Termin für den Filmabend (Einladung) und TMDB-Stichworte je Film (Prognose).

Revision ID: 0002
Revises: 0001
Created: 2026-10-03 21:53:58.437514
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Before committing, check:
# - a new NOT NULL column needs server_default=..., or SQLite refuses it on
#   tables that already have rows;
# - renames come out as drop + add (data lost): use batch_op.alter_column(new_column_name=...);
# - a failed upgrade is rolled back; the app then refuses to start until fixed.


def upgrade() -> None:
    op.create_table(
        "abend",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("termin", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("notiz", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("gesetzt_von", sa.Integer(), nullable=True),
        sa.Column("gesetzt_am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["gesetzt_von"], ["user.id"], name=op.f("fk_abend_gesetzt_von_user"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_abend")),
    )
    with op.batch_alter_table("movie", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("keywords", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="")
        )


def downgrade() -> None:
    with op.batch_alter_table("movie", schema=None) as batch_op:
        batch_op.drop_column("keywords")

    op.drop_table("abend")
