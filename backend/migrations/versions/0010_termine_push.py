"""Termine finden, zusagen, erinnern: Umfrage, Rückmeldungen, Kalender und Push.

- terminvorschlag, terminstimme: die Terminumfrage einer Gruppe
- mitglied.rueckmeldung: „vielleicht“ oder „nein“ (zugesagt bleibt mitglied.dabei)
- user.kalender: Token des persönlichen Kalender-Abos
- user.push, pushabo: welche Push-Nachrichten jemand will, und an welche Geräte
- appmeta.vapid: der VAPID-Schlüssel des Servers für Web Push
- abend.erinnert: für welchen Termin die Erinnerung schon rausging

Revision ID: 0010
Revises: 0009
Created: 2026-10-06 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text(name: str) -> sa.Column:
    """A NOT NULL text column for a table that already has rows."""
    return sa.Column(name, sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="")


def upgrade() -> None:
    op.create_table(
        "terminvorschlag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gruppe_id", sa.Integer(), nullable=False),
        sa.Column("termin", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("notiz", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("von_id", sa.Integer(), nullable=True),
        sa.Column("am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_terminvorschlag_gruppe_id_gruppe"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["von_id"], ["user.id"], name=op.f("fk_terminvorschlag_von_id_user"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_terminvorschlag")),
    )
    with op.batch_alter_table("terminvorschlag", schema=None) as b:
        b.create_index(b.f("ix_terminvorschlag_gruppe_id"), ["gruppe_id"], unique=False)

    op.create_table(
        "terminstimme",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vorschlag_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("antwort", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["vorschlag_id"],
            ["terminvorschlag.id"],
            name=op.f("fk_terminstimme_vorschlag_id_terminvorschlag"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_terminstimme_user_id_user"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_terminstimme")),
        sa.UniqueConstraint("vorschlag_id", "user_id", name=op.f("uq_terminstimme_vorschlag_id_user_id")),
    )
    with op.batch_alter_table("terminstimme", schema=None) as b:
        b.create_index(b.f("ix_terminstimme_vorschlag_id"), ["vorschlag_id"], unique=False)

    op.create_table(
        "pushabo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("p256dh", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("auth", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("geraet", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_pushabo_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pushabo")),
        sa.UniqueConstraint("endpoint", name=op.f("uq_pushabo_endpoint")),
    )
    with op.batch_alter_table("pushabo", schema=None) as b:
        b.create_index(b.f("ix_pushabo_user_id"), ["user_id"], unique=False)

    with op.batch_alter_table("abend", schema=None) as b:
        b.add_column(sa.Column("erinnert", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True))
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.add_column(_text("vapid"))
    with op.batch_alter_table("mitglied", schema=None) as b:
        b.add_column(_text("rueckmeldung"))
    with op.batch_alter_table("user", schema=None) as b:
        b.add_column(_text("kalender"))
        b.add_column(_text("push"))


def downgrade() -> None:
    with op.batch_alter_table("user", schema=None) as b:
        b.drop_column("push")
        b.drop_column("kalender")
    with op.batch_alter_table("mitglied", schema=None) as b:
        b.drop_column("rueckmeldung")
    with op.batch_alter_table("appmeta", schema=None) as b:
        b.drop_column("vapid")
    with op.batch_alter_table("abend", schema=None) as b:
        b.drop_column("erinnert")
    with op.batch_alter_table("pushabo", schema=None) as b:
        b.drop_index(b.f("ix_pushabo_user_id"))
    op.drop_table("pushabo")
    with op.batch_alter_table("terminstimme", schema=None) as b:
        b.drop_index(b.f("ix_terminstimme_vorschlag_id"))
    op.drop_table("terminstimme")
    with op.batch_alter_table("terminvorschlag", schema=None) as b:
        b.drop_index(b.f("ix_terminvorschlag_gruppe_id"))
    op.drop_table("terminvorschlag")
