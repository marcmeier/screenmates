"""Schema migrations: fresh installs, adopting pre-Alembic databases, and models in sync."""

import sqlite3

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

from app import (
    migrate,
    models,  # noqa: F401  (register tables)
)


def url(tmp_path, name="db.sqlite"):
    return f"sqlite:///{tmp_path / name}"


def tables(db_url):
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            return set(inspect(conn).get_table_names())
    finally:
        engine.dispose()


def test_fresh_database_gets_every_table(tmp_path):
    u = url(tmp_path)
    migrate.upgrade(u)
    assert set(SQLModel.metadata.tables) <= tables(u)
    assert migrate.current_revision(u) == migrate.head_revision()


def test_migrations_match_the_models(tmp_path):
    """Fails when a model changes without a migration: run `make migration name=...`."""
    u = url(tmp_path)
    migrate.upgrade(u)
    engine = create_engine(u)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
    engine.dispose()
    assert diff == []


def test_upgrade_is_idempotent(tmp_path):
    u = url(tmp_path)
    migrate.upgrade(u)
    migrate.upgrade(u)
    assert migrate.current_revision(u) == migrate.head_revision()


def test_database_from_before_migrations_is_adopted_with_its_data(tmp_path):
    """0.2/0.3 created tables with create_all; abo/veto/abend and movie.keywords came later."""
    from alembic import command

    u = url(tmp_path)
    command.upgrade(migrate.alembic_config(u), "0001")  # the baseline is what 0.2/0.3 had …
    con = sqlite3.connect(tmp_path / "db.sqlite")
    con.execute("drop table alembic_version")  # … without Alembic,
    con.execute("drop table abo")  # and without what came in 0.4
    con.execute("drop table veto")
    con.execute("PRAGMA user_version = 2")
    con.execute("insert into user (id, name, color, dabei, created_at) values (1, 'Marc', '#e50914', 0, '2026-10-03')")
    con.execute(
        "insert into movie (id, media_type, title, original_title, overview, release_date, poster_path, backdrop_path,"
        " vote_average, vote_count, popularity, genres, collection, is_canon, added_at)"
        " values (694, 'movie', 'Shining', '', '', '', '', '', 8.2, 1, 1, '[]', '', 1, '2026-10-03')"
    )
    con.commit()
    con.close()

    migrate.upgrade(u)

    assert {"abo", "veto", "abend", "gruppe", "alembic_version"} <= tables(u)
    assert migrate.current_revision(u) == migrate.head_revision()
    con = sqlite3.connect(tmp_path / "db.sqlite")
    assert con.execute("select name from user").fetchall() == [("Marc",)]
    assert con.execute("select title, keywords from movie").fetchall() == [("Shining", "")]
    # Everyone lands in the first group.
    assert con.execute("select gruppe_id, user_id from mitglied").fetchall() == [(1, 1)]


def test_0013_keeps_logged_in_browsers_and_drops_the_film_password(tmp_path):
    from alembic import command

    u = url(tmp_path)
    command.upgrade(migrate.alembic_config(u), "0012")
    con = sqlite3.connect(tmp_path / "db.sqlite")
    con.execute(
        "insert into user (id, name, color, design, obs_key, schutz_movie_id, is_admin, freigegeben, bild, vitrine,"
        " kalender, push, created_at) values (1, 'Marc', '', '', '', 694, 1, 1, '', '[]', '', '', '2026-10-03')"
    )
    con.execute(  # group 1 exists since 0006
        "insert into mitglied (gruppe_id, user_id, ist_admin, dabei, rueckmeldung, seit)"
        " values (1, 1, 1, 0, '', '2026-10-03')"
    )
    con.execute("insert into session (sid, user_id, zugang, created_at) values ('drin', 1, 1, '2026-10-04')")
    con.execute("insert into session (sid, user_id, zugang, created_at) values ('draussen', null, 1, '2026-10-04')")
    con.commit()
    con.close()

    migrate.upgrade(u)

    con = sqlite3.connect(tmp_path / "db.sqlite")
    assert con.execute("select sid, user_id from sessionname").fetchall() == [("drin", 1)]
    assert "schutz_movie_id" not in [r[1] for r in con.execute("pragma table_info(user)")]
    assert con.execute("select user_id, ist_admin from mitglied").fetchall() == [(1, 1)]  # the rebuild kept children


def test_0015_keeps_german_time_for_databases_from_before(tmp_path):
    from alembic import command

    u = url(tmp_path)
    command.upgrade(migrate.alembic_config(u), "0014")
    con = sqlite3.connect(tmp_path / "db.sqlite")
    con.execute(
        "insert into user (id, name, color, design, obs_key, is_admin, freigegeben, bild, vitrine, kalender, push,"
        " created_at) values (1, 'Marc', '', '', '', 1, 1, '', '[]', '', '', '2026-10-03')"
    )
    con.commit()
    con.close()
    migrate.upgrade(u)
    con = sqlite3.connect(tmp_path / "db.sqlite")
    assert con.execute("select zeitzone from appmeta").fetchall() == [("Europe/Berlin",)]

    assert con.execute("select wuensche from appmeta").fetchall() == [(1,)]  # 0016: in use, so it stays on

    frisch = url(tmp_path, "frisch.sqlite")  # a new install: its first admin decides
    migrate.upgrade(frisch)
    con = sqlite3.connect(tmp_path / "frisch.sqlite")
    assert con.execute("select zeitzone, wuensche from appmeta").fetchall() in ([], [("", 0)])


def test_database_from_0_1_is_refused(tmp_path):
    con = sqlite3.connect(tmp_path / "db.sqlite")
    con.execute("create table user (id integer primary key, name text)")  # user_version stays 0
    con.close()
    with pytest.raises(migrate.OutdatedDatabaseError):
        migrate.upgrade(url(tmp_path))


def test_migrations_run_with_foreign_keys_off(tmp_path, monkeypatch):
    """A table rebuild with foreign keys on would cascade-delete every child row."""
    seen = []
    from alembic.runtime import migration

    original = migration.MigrationContext.run_migrations

    def spy(self, **kw):
        seen.append(self.connection.exec_driver_sql("PRAGMA foreign_keys").scalar())
        return original(self, **kw)

    monkeypatch.setattr(migration.MigrationContext, "run_migrations", spy)
    migrate.upgrade(url(tmp_path))
    assert seen == [0]
