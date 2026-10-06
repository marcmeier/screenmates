"""Kino-Chat dauerhaft: Nachrichten bleiben 30 Tage (vorher nur im Speicher).

Revision ID: 0011
Revises: 0010
Created: 2026-10-06 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kinonachricht",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gruppe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_kinonachricht_gruppe_id_gruppe"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_kinonachricht_user_id_user"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kinonachricht")),
    )
    with op.batch_alter_table("kinonachricht", schema=None) as b:
        b.create_index(b.f("ix_kinonachricht_gruppe_id"), ["gruppe_id"], unique=False)
        b.create_index(b.f("ix_kinonachricht_am"), ["am"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("kinonachricht", schema=None) as b:
        b.drop_index(b.f("ix_kinonachricht_am"))
        b.drop_index(b.f("ix_kinonachricht_gruppe_id"))
    op.drop_table("kinonachricht")
