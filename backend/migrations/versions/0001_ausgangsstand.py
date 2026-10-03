"""Ausgangsstand: das Schema von screenmates 0.3/0.4.

Legt jede Tabelle nur an, wenn sie fehlt - so übernimmt die Migration auch
Datenbanken, die vor Alembic mit create_all entstanden sind.

Revision ID: 0001
Revises:
Created: 2026-10-03 21:25:53.450863
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.sql.sqltypes.AutoString)
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotent on purpose: databases from before migrations existed (created
    # with create_all) keep their tables and only get the ones they lack.
    vorhanden = set(sa.inspect(op.get_bind()).get_table_names())

    if "appmeta" not in vorhanden:
        op.create_table(
            "appmeta",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("last_sync", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_appmeta")),
        )
    if "hoststate" not in vorhanden:
        op.create_table(
            "hoststate",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("movie_id", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_hoststate")),
        )
    if "info" not in vorhanden:
        op.create_table(
            "info",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_info")),
        )
    if "kinostate" not in vorhanden:
        op.create_table(
            "kinostate",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("secret", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("obs_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("titel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("movie_id", sa.Integer(), nullable=True),
            sa.Column("gestartet", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_kinostate")),
        )
    if "movie" not in vorhanden:
        op.create_table(
            "movie",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("media_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("original_title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("overview", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("release_date", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("runtime", sa.Integer(), nullable=True),
            sa.Column("poster_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("backdrop_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("vote_average", sa.Float(), nullable=False),
            sa.Column("vote_count", sa.Integer(), nullable=False),
            sa.Column("popularity", sa.Float(), nullable=False),
            sa.Column("genres", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("collection", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("is_canon", sa.Boolean(), nullable=False),
            sa.Column("added_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_movie")),
        )
    if "movie" not in vorhanden:
        with op.batch_alter_table("movie", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_movie_is_canon"), ["is_canon"], unique=False)
            batch_op.create_index(batch_op.f("ix_movie_media_type"), ["media_type"], unique=False)
            batch_op.create_index(batch_op.f("ix_movie_year"), ["year"], unique=False)

    if "user" not in vorhanden:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("color", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("schutz_movie_id", sa.Integer(), nullable=True),
            sa.Column("dabei", sa.Boolean(), nullable=False),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
        )
    if "user" not in vorhanden:
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_user_name"), ["name"], unique=True)

    if "abo" not in vorhanden:
        op.create_table(
            "abo",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_abo_user_id_user"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_abo")),
            sa.UniqueConstraint("user_id", "provider_id", name=op.f("uq_abo_user_id_provider_id")),
        )
    if "abo" not in vorhanden:
        with op.batch_alter_table("abo", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_abo_user_id"), ["user_id"], unique=False)

    if "feature" not in vorhanden:
        op.create_table(
            "feature",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("done", sa.Boolean(), nullable=False),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_feature_user_id_user"), ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_feature")),
        )
    if "session" not in vorhanden:
        op.create_table(
            "session",
            sa.Column("sid", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("is_host", sa.Boolean(), nullable=False),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_session_user_id_user"), ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("sid", name=op.f("pk_session")),
        )
    if "suggestion" not in vorhanden:
        op.create_table(
            "suggestion",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("movie_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["movie_id"], ["movie.id"], name=op.f("fk_suggestion_movie_id_movie"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_suggestion_user_id_user"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_suggestion")),
            sa.UniqueConstraint("movie_id", "user_id", name=op.f("uq_suggestion_movie_id_user_id")),
        )
    if "suggestion" not in vorhanden:
        with op.batch_alter_table("suggestion", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_suggestion_movie_id"), ["movie_id"], unique=False)

    if "veto" not in vorhanden:
        op.create_table(
            "veto",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("movie_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["movie_id"], ["movie.id"], name=op.f("fk_veto_movie_id_movie"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_veto_user_id_user"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_veto")),
            sa.UniqueConstraint("user_id", name=op.f("uq_veto_user_id")),
        )
    if "veto" not in vorhanden:
        with op.batch_alter_table("veto", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_veto_movie_id"), ["movie_id"], unique=False)

    if "watched" not in vorhanden:
        op.create_table(
            "watched",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("movie_id", sa.Integer(), nullable=False),
            sa.Column("watched_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.Column("hidden", sa.Boolean(), nullable=False),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["movie_id"], ["movie.id"], name=op.f("fk_watched_movie_id_movie"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_watched")),
        )
    if "watched" not in vorhanden:
        with op.batch_alter_table("watched", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_watched_movie_id"), ["movie_id"], unique=False)

    if "wishlist" not in vorhanden:
        op.create_table(
            "wishlist",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("movie_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["movie_id"], ["movie.id"], name=op.f("fk_wishlist_movie_id_movie"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_wishlist_user_id_user"), ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_wishlist")),
            sa.UniqueConstraint("movie_id", name=op.f("uq_wishlist_movie_id")),
        )
    if "featurenote" not in vorhanden:
        op.create_table(
            "featurenote",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("feature_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["feature_id"], ["feature.id"], name=op.f("fk_featurenote_feature_id_feature"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_featurenote_user_id_user"), ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_featurenote")),
        )
    if "featurenote" not in vorhanden:
        with op.batch_alter_table("featurenote", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_featurenote_feature_id"), ["feature_id"], unique=False)

    if "featurevote" not in vorhanden:
        op.create_table(
            "featurevote",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("feature_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["feature_id"], ["feature.id"], name=op.f("fk_featurevote_feature_id_feature"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_featurevote_user_id_user"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_featurevote")),
            sa.UniqueConstraint("feature_id", "user_id", name=op.f("uq_featurevote_feature_id_user_id")),
        )
    if "featurevote" not in vorhanden:
        with op.batch_alter_table("featurevote", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_featurevote_feature_id"), ["feature_id"], unique=False)

    if "watchednote" not in vorhanden:
        op.create_table(
            "watchednote",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("watched_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["parent_id"], ["watchednote.id"], name=op.f("fk_watchednote_parent_id_watchednote"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_watchednote_user_id_user"), ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["watched_id"], ["watched.id"], name=op.f("fk_watchednote_watched_id_watched"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_watchednote")),
        )
    if "watchednote" not in vorhanden:
        with op.batch_alter_table("watchednote", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_watchednote_watched_id"), ["watched_id"], unique=False)

    if "watchedparticipant" not in vorhanden:
        op.create_table(
            "watchedparticipant",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("watched_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_watchedparticipant_user_id_user"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["watched_id"],
                ["watched.id"],
                name=op.f("fk_watchedparticipant_watched_id_watched"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_watchedparticipant")),
            sa.UniqueConstraint("watched_id", "user_id", name=op.f("uq_watchedparticipant_watched_id_user_id")),
        )
    if "watchedparticipant" not in vorhanden:
        with op.batch_alter_table("watchedparticipant", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_watchedparticipant_user_id"), ["user_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_watchedparticipant_watched_id"), ["watched_id"], unique=False)

    if "watchedrating" not in vorhanden:
        op.create_table(
            "watchedrating",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("watched_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("stars", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_watchedrating_user_id_user"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["watched_id"], ["watched.id"], name=op.f("fk_watchedrating_watched_id_watched"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_watchedrating")),
            sa.UniqueConstraint("watched_id", "user_id", name=op.f("uq_watchedrating_watched_id_user_id")),
        )
    if "watchedrating" not in vorhanden:
        with op.batch_alter_table("watchedrating", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_watchedrating_watched_id"), ["watched_id"], unique=False)

    if "noteheart" not in vorhanden:
        op.create_table(
            "noteheart",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("note_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["note_id"], ["watchednote.id"], name=op.f("fk_noteheart_note_id_watchednote"), ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["user.id"], name=op.f("fk_noteheart_user_id_user"), ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_noteheart")),
            sa.UniqueConstraint("note_id", "user_id", name=op.f("uq_noteheart_note_id_user_id")),
        )
    if "noteheart" not in vorhanden:
        with op.batch_alter_table("noteheart", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_noteheart_note_id"), ["note_id"], unique=False)


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("noteheart", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_noteheart_note_id"))

    op.drop_table("noteheart")
    with op.batch_alter_table("watchedrating", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_watchedrating_watched_id"))

    op.drop_table("watchedrating")
    with op.batch_alter_table("watchedparticipant", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_watchedparticipant_watched_id"))
        batch_op.drop_index(batch_op.f("ix_watchedparticipant_user_id"))

    op.drop_table("watchedparticipant")
    with op.batch_alter_table("watchednote", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_watchednote_watched_id"))

    op.drop_table("watchednote")
    with op.batch_alter_table("featurevote", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_featurevote_feature_id"))

    op.drop_table("featurevote")
    with op.batch_alter_table("featurenote", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_featurenote_feature_id"))

    op.drop_table("featurenote")
    op.drop_table("wishlist")
    with op.batch_alter_table("watched", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_watched_movie_id"))

    op.drop_table("watched")
    with op.batch_alter_table("veto", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_veto_movie_id"))

    op.drop_table("veto")
    with op.batch_alter_table("suggestion", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_suggestion_movie_id"))

    op.drop_table("suggestion")
    op.drop_table("session")
    op.drop_table("feature")
    with op.batch_alter_table("abo", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_abo_user_id"))

    op.drop_table("abo")
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_name"))

    op.drop_table("user")
    with op.batch_alter_table("movie", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_movie_year"))
        batch_op.drop_index(batch_op.f("ix_movie_media_type"))
        batch_op.drop_index(batch_op.f("ix_movie_is_canon"))

    op.drop_table("movie")
    op.drop_table("kinostate")
    op.drop_table("info")
    op.drop_table("hoststate")
    op.drop_table("appmeta")
    # ### end Alembic commands ###
