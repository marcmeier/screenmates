"""Gemeinsame Kistenöffnung (der Gastgeber öffnet, alle schauen zu) und Kommentar-Platzhalter.

- kistenoeffnung: Gewinner, Startwert fürs Band, Startzeit, pro Gruppe
- watchednote.geloescht: gelöscht, obwohl jemand geantwortet hat ("ersteller" | "admin")
- kianfrage: jede KI-Suche mit Modell, Tokens und Kosten, für die Verwaltung

Revision ID: 0008
Revises: 0007
Created: 2026-10-06 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kistenoeffnung",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gruppe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("pool", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("start", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("erledigt", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_kistenoeffnung_gruppe_id_gruppe"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["movie_id"], ["movie.id"], name=op.f("fk_kistenoeffnung_movie_id_movie"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_kistenoeffnung_user_id_user"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kistenoeffnung")),
    )
    with op.batch_alter_table("kistenoeffnung", schema=None) as b:
        b.create_index(b.f("ix_kistenoeffnung_gruppe_id"), ["gruppe_id"], unique=False)
    with op.batch_alter_table("watchednote", schema=None) as b:
        b.add_column(sa.Column("geloescht", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""))
    op.create_table(
        "kianfrage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("gruppe_id", sa.Integer(), nullable=True),
        sa.Column("modell", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tokens_ein", sa.Integer(), nullable=False),
        sa.Column("tokens_aus", sa.Integer(), nullable=False),
        sa.Column("kosten", sa.Float(), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("fehler", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_kianfrage_gruppe_id_gruppe"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_kianfrage_user_id_user"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kianfrage")),
    )
    with op.batch_alter_table("kianfrage", schema=None) as b:
        b.create_index(b.f("ix_kianfrage_at"), ["at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("kianfrage", schema=None) as b:
        b.drop_index(b.f("ix_kianfrage_at"))
    op.drop_table("kianfrage")
    with op.batch_alter_table("watchednote", schema=None) as b:
        b.drop_column("geloescht")
    with op.batch_alter_table("kistenoeffnung", schema=None) as b:
        b.drop_index(b.f("ix_kistenoeffnung_gruppe_id"))
    op.drop_table("kistenoeffnung")
