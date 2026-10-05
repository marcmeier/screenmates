"""Gruppen: unabhängige Freundeskreise auf einem Server.

- gruppe, mitglied (Gruppen-Admin, „bin dabei“ pro Gruppe statt user.dabei)
- watched, wishlist, suggestion, veto: gruppe_id; Eindeutigkeit gilt pro Gruppe
- session.gruppe_id: die aktive Gruppe des Browsers
- abend, info, kinostate: ihre id ist ab jetzt die Gruppen-ID (keine Schemaänderung)

Alles Bisherige landet in „Unsere Gruppe“ (id 1) mit allen freigegebenen Namen;
wer Admin war, wird dort Gruppen-Admin.

Revision ID: 0006
Revises: 0005
Created: 2026-10-05 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# table -> (old unique constraint, new unique columns)
EINDEUTIG = {
    "watched": (None, None),
    "wishlist": ("uq_wishlist_movie_id", ["gruppe_id", "movie_id"]),
    "suggestion": ("uq_suggestion_movie_id_user_id", ["gruppe_id", "movie_id", "user_id"]),
    "veto": ("uq_veto_user_id", ["gruppe_id", "user_id"]),
}


def upgrade() -> None:
    op.create_table(
        "gruppe",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gruppe")),
        sa.UniqueConstraint("name", name=op.f("uq_gruppe_name")),
    )
    op.create_table(
        "mitglied",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gruppe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ist_admin", sa.Boolean(), nullable=False),
        sa.Column("dabei", sa.Boolean(), nullable=False),
        sa.Column("seit", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gruppe_id"], ["gruppe.id"], name=op.f("fk_mitglied_gruppe_id_gruppe"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_mitglied_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mitglied")),
        sa.UniqueConstraint("gruppe_id", "user_id", name=op.f("uq_mitglied_gruppe_id_user_id")),
    )
    with op.batch_alter_table("mitglied", schema=None) as b:
        b.create_index(b.f("ix_mitglied_gruppe_id"), ["gruppe_id"], unique=False)
        b.create_index(b.f("ix_mitglied_user_id"), ["user_id"], unique=False)

    conn = op.get_bind()
    conn.execute(sa.text("INSERT INTO gruppe (id, name, created_at) VALUES (1, 'Unsere Gruppe', CURRENT_TIMESTAMP)"))
    conn.execute(
        sa.text(
            "INSERT INTO mitglied (gruppe_id, user_id, ist_admin, dabei, seit) "
            "SELECT 1, id, is_admin, dabei, created_at FROM user WHERE freigegeben"
        )
    )

    for tabelle, (alt, neu) in EINDEUTIG.items():
        with op.batch_alter_table(tabelle, schema=None) as b:
            b.add_column(sa.Column("gruppe_id", sa.Integer(), nullable=False, server_default="1"))
            b.create_index(b.f(f"ix_{tabelle}_gruppe_id"), ["gruppe_id"], unique=False)
            b.create_foreign_key(
                b.f(f"fk_{tabelle}_gruppe_id_gruppe"), "gruppe", ["gruppe_id"], ["id"], ondelete="CASCADE"
            )
            if alt:
                b.drop_constraint(alt, type_="unique")
                b.create_unique_constraint(b.f(f"uq_{tabelle}_{'_'.join(neu)}"), neu)
        with op.batch_alter_table(tabelle, schema=None) as b:
            b.alter_column("gruppe_id", server_default=None)

    with op.batch_alter_table("session", schema=None) as b:
        b.add_column(sa.Column("gruppe_id", sa.Integer(), nullable=True))
        b.create_foreign_key(b.f("fk_session_gruppe_id_gruppe"), "gruppe", ["gruppe_id"], ["id"], ondelete="SET NULL")
    with op.batch_alter_table("user", schema=None) as b:
        b.drop_column("dabei")


def downgrade() -> None:
    with op.batch_alter_table("user", schema=None) as b:
        b.add_column(sa.Column("dabei", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.execute("UPDATE user SET dabei = 1 WHERE id IN (SELECT user_id FROM mitglied WHERE gruppe_id = 1 AND dabei)")
    with op.batch_alter_table("session", schema=None) as b:
        b.drop_constraint("fk_session_gruppe_id_gruppe", type_="foreignkey")
        b.drop_column("gruppe_id")
    for tabelle, (alt, neu) in EINDEUTIG.items():
        op.execute(f"DELETE FROM {tabelle} WHERE gruppe_id != 1")
        with op.batch_alter_table(tabelle, schema=None) as b:
            if alt:
                b.drop_constraint(f"uq_{tabelle}_{'_'.join(neu)}", type_="unique")
                cols = [c for c in neu if c != "gruppe_id"]
                b.create_unique_constraint(alt, cols)
            b.drop_constraint(f"fk_{tabelle}_gruppe_id_gruppe", type_="foreignkey")
            b.drop_index(f"ix_{tabelle}_gruppe_id")
            b.drop_column("gruppe_id")
    op.drop_table("mitglied")
    op.drop_table("gruppe")
