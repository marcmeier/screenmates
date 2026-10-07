"""Names belong to browsers: session names and one-time login codes replace the film password.

Every browser that is logged in today keeps its name. The film password column goes.

Revision ID: 0013
Revises: 0012
Created: 2026-10-07 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessionname",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sid", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sid"], ["session.sid"], name=op.f("fk_sessionname_sid_session"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_sessionname_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessionname")),
        sa.UniqueConstraint("sid", "user_id", name=op.f("uq_sessionname_sid_user_id")),
    )
    with op.batch_alter_table("sessionname", schema=None) as b:
        b.create_index(b.f("ix_sessionname_sid"), ["sid"], unique=False)
        b.create_index(b.f("ix_sessionname_user_id"), ["user_id"], unique=False)
    op.create_table(
        "logincode",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("valid_until", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user.id"], name=op.f("fk_logincode_created_by_user"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_logincode_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_logincode")),
        sa.UniqueConstraint("code_hash", name=op.f("uq_logincode_code_hash")),
    )
    with op.batch_alter_table("logincode", schema=None) as b:
        b.create_index(b.f("ix_logincode_user_id"), ["user_id"], unique=False)

    # Whoever is logged in now keeps their name on that browser.
    op.execute(
        "INSERT INTO sessionname (sid, user_id, created_at) "
        "SELECT sid, user_id, created_at FROM session WHERE user_id IS NOT NULL"
    )
    with op.batch_alter_table("user", schema=None) as b:
        b.drop_column("schutz_movie_id")


def downgrade() -> None:
    with op.batch_alter_table("user", schema=None) as b:
        b.add_column(sa.Column("schutz_movie_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("logincode", schema=None) as b:
        b.drop_index(b.f("ix_logincode_user_id"))
    op.drop_table("logincode")
    with op.batch_alter_table("sessionname", schema=None) as b:
        b.drop_index(b.f("ix_sessionname_user_id"))
        b.drop_index(b.f("ix_sessionname_sid"))
    op.drop_table("sessionname")
