"""Die Glocke: Benachrichtigungen auch in der App (30 Tage).

Revision ID: 0012
Revises: 0011
Created: 2026-10-06 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benachrichtigung",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("art", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("titel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("am", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("gelesen", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_benachrichtigung_user_id_user"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_benachrichtigung")),
    )
    with op.batch_alter_table("benachrichtigung", schema=None) as b:
        b.create_index(b.f("ix_benachrichtigung_user_id"), ["user_id"], unique=False)
        b.create_index(b.f("ix_benachrichtigung_am"), ["am"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("benachrichtigung", schema=None) as b:
        b.drop_index(b.f("ix_benachrichtigung_am"))
        b.drop_index(b.f("ix_benachrichtigung_user_id"))
    op.drop_table("benachrichtigung")
