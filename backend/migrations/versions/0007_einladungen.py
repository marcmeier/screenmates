"""Einladungen statt Zugangsfrage.

- einladung: Links pro Gruppe (direkt aufnehmen oder Antrag, Ablauf, Nutzungslimit, widerrufbar)
- beitrittsanfrage: wer schon einen Namen hat und per Link in eine weitere Gruppe möchte
- session.einladung_id: mit welcher Einladung der Browser hereinkam
- user.antrag_gruppe_id: zu welcher Gruppe ein beantragter Name gehört
- zugang (die Zugangsfrage) fällt weg; wer schon drin ist, bleibt drin

Revision ID: 0007
Revises: 0006
Created: 2026-10-05 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "einladung",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("gruppe_id", sa.Integer(), nullable=False),
        sa.Column("erstellt_von", sa.Integer(), nullable=True),
        sa.Column("erstellt_am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("gueltig_bis", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("max_nutzungen", sa.Integer(), nullable=True),
        sa.Column("nutzungen", sa.Integer(), nullable=False),
        sa.Column("direkt", sa.Boolean(), nullable=False),
        sa.Column("widerrufen", sa.Boolean(), nullable=False),
        sa.Column("notiz", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["erstellt_von"], ["user.id"], name=op.f("fk_einladung_erstellt_von_user"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_einladung_gruppe_id_gruppe"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_einladung")),
    )
    with op.batch_alter_table("einladung", schema=None) as b:
        b.create_index(b.f("ix_einladung_gruppe_id"), ["gruppe_id"], unique=False)
        b.create_index(b.f("ix_einladung_token"), ["token"], unique=True)
    op.create_table(
        "beitrittsanfrage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gruppe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("einladung_id", sa.Integer(), nullable=True),
        sa.Column("am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["einladung_id"],
            ["einladung.id"],
            name=op.f("fk_beitrittsanfrage_einladung_id_einladung"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_beitrittsanfrage_gruppe_id_gruppe"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_beitrittsanfrage_user_id_user"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beitrittsanfrage")),
        sa.UniqueConstraint("gruppe_id", "user_id", name=op.f("uq_beitrittsanfrage_gruppe_id_user_id")),
    )
    with op.batch_alter_table("beitrittsanfrage", schema=None) as b:
        b.create_index(b.f("ix_beitrittsanfrage_gruppe_id"), ["gruppe_id"], unique=False)
    with op.batch_alter_table("session", schema=None) as b:
        b.add_column(sa.Column("einladung_id", sa.Integer(), nullable=True))
        b.create_foreign_key(
            b.f("fk_session_einladung_id_einladung"), "einladung", ["einladung_id"], ["id"], ondelete="SET NULL"
        )
    with op.batch_alter_table("user", schema=None) as b:
        b.add_column(sa.Column("antrag_gruppe_id", sa.Integer(), nullable=True))
        b.create_foreign_key(
            b.f("fk_user_antrag_gruppe_id_gruppe"), "gruppe", ["antrag_gruppe_id"], ["id"], ondelete="SET NULL"
        )
    op.drop_table("zugang")


def downgrade() -> None:
    op.create_table(
        "zugang",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("frage", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=True),
        sa.Column("titel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("geaendert", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zugang")),
    )
    with op.batch_alter_table("user", schema=None) as b:
        b.drop_constraint("fk_user_antrag_gruppe_id_gruppe", type_="foreignkey")
        b.drop_column("antrag_gruppe_id")
    with op.batch_alter_table("session", schema=None) as b:
        b.drop_constraint("fk_session_einladung_id_einladung", type_="foreignkey")
        b.drop_column("einladung_id")
    op.drop_table("beitrittsanfrage")
    op.drop_table("einladung")
