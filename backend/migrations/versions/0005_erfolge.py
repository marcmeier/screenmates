"""Erfolge: freigeschaltete Erfolge, ein Ereignisprotokoll und die Vitrine.

- erfolg: wer hat was seit wann (gesehen = Pop-up gezeigt, entzogen = von Admins entzogen)
- ereignis: was sich später nicht aus den Daten lesen lässt (Termin gesetzt, Kino gesendet/geschaut,
  Vorschlag wurde geschaut)
- user.vitrine: bis zu drei Erfolge fürs Profil (JSON)
- appmeta.erfolge_seit: alles davor zählt so, wie es ist (einmalig, rückwirkend)

Revision ID: 0005
Revises: 0004
Created: 2026-10-05 15:00:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "erfolg",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("schluessel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("gesehen", sa.Boolean(), nullable=False),
        sa.Column("rueckwirkend", sa.Boolean(), nullable=False),
        sa.Column("entzogen", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_erfolg_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_erfolg")),
        sa.UniqueConstraint("user_id", "schluessel", name=op.f("uq_erfolg_user_id_schluessel")),
    )
    with op.batch_alter_table("erfolg", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_erfolg_user_id"), ["user_id"], unique=False)
    op.create_table(
        "ereignis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("typ", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("bezug", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_ereignis_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ereignis")),
    )
    with op.batch_alter_table("ereignis", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ereignis_typ"), ["typ"], unique=False)
        batch_op.create_index(batch_op.f("ix_ereignis_user_id"), ["user_id"], unique=False)
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("vitrine", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="[]")
        )
    with op.batch_alter_table("appmeta", schema=None) as batch_op:
        batch_op.add_column(sa.Column("erfolge_seit", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True))
        batch_op.add_column(sa.Column("erfolge_geprueft", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    # Everything up to now counts as it is; from here on the stricter rules apply.
    jetzt = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT count(*) FROM appmeta WHERE id = 1")).scalar():
        conn.execute(sa.text("UPDATE appmeta SET erfolge_seit = :t WHERE id = 1"), {"t": jetzt})
    else:
        conn.execute(
            sa.text("INSERT INTO appmeta (id, erfolge_seit, erfolge_geprueft) VALUES (1, :t, 0)"), {"t": jetzt}
        )


def downgrade() -> None:
    with op.batch_alter_table("appmeta", schema=None) as batch_op:
        batch_op.drop_column("erfolge_geprueft")
        batch_op.drop_column("erfolge_seit")
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("vitrine")
    with op.batch_alter_table("ereignis", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ereignis_user_id"))
        batch_op.drop_index(batch_op.f("ix_ereignis_typ"))
    op.drop_table("ereignis")
    with op.batch_alter_table("erfolg", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_erfolg_user_id"))
    op.drop_table("erfolg")
