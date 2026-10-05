"""Gastgeber-Stab: wer den Abend führt, und wie die Rolle wechselt.

- abend.gastgeber_id: hält den Stab (vorbelegt mit dem, der den Termin gesetzt hat)
- stabwechsel: Übergaben, Übernahmen und Abstimmungen
- user.obs_key: persönlicher OBS-Schlüssel, gilt nur mit dem Stab

Revision ID: 0009
Revises: 0008
Created: 2026-10-06 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("abend", schema=None) as b:
        b.add_column(sa.Column("gastgeber_id", sa.Integer(), nullable=True))
        b.create_foreign_key(b.f("fk_abend_gastgeber_id_user"), "user", ["gastgeber_id"], ["id"], ondelete="SET NULL")
    op.execute("UPDATE abend SET gastgeber_id = gesetzt_von")
    with op.batch_alter_table("user", schema=None) as b:
        b.add_column(sa.Column("obs_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""))
    op.create_table(
        "stabwechsel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gruppe_id", sa.Integer(), nullable=False),
        sa.Column("art", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("von_id", sa.Integer(), nullable=True),
        sa.Column("an_id", sa.Integer(), nullable=True),
        sa.Column("frist", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("stimmen", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("erledigt_am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_stabwechsel_gruppe_id_gruppe"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["von_id"], ["user.id"], name=op.f("fk_stabwechsel_von_id_user"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["an_id"], ["user.id"], name=op.f("fk_stabwechsel_an_id_user"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stabwechsel")),
    )
    with op.batch_alter_table("stabwechsel", schema=None) as b:
        b.create_index(b.f("ix_stabwechsel_gruppe_id"), ["gruppe_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("stabwechsel", schema=None) as b:
        b.drop_index(b.f("ix_stabwechsel_gruppe_id"))
    op.drop_table("stabwechsel")
    with op.batch_alter_table("user", schema=None) as b:
        b.drop_column("obs_key")
    with op.batch_alter_table("abend", schema=None) as b:
        b.drop_constraint(b.f("fk_abend_gastgeber_id_user"), type_="foreignkey")
        b.drop_column("gastgeber_id")
