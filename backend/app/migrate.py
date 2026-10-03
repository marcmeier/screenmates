"""Bring the database to the newest schema on startup (Alembic).

Three cases:

- empty database: the baseline migration creates everything;
- database from before migrations existed (0.2/0.3, made with create_all):
  the baseline is idempotent, keeps every existing table and only adds the
  ones that are missing; later migrations then apply as usual;
- database from 0.1 (no foreign keys, different tables): refused with a clear
  message instead of migrating something we can't vouch for.

New schema changes go into a new revision: `make migration name="..."`.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from .config import settings

BACKEND = Path(__file__).resolve().parent.parent
# Databases from 0.2 and 0.3 carry this in PRAGMA user_version.
LEGACY_SCHEMA_VERSION = 2


class OutdatedDatabaseError(RuntimeError):
    pass


def alembic_config(url: str | None = None) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.attributes["url"] = url or settings.database_url
    cfg.attributes["configure_logger"] = False  # keep uvicorn's logging as it is
    return cfg


def head_revision(cfg: Config | None = None) -> str:
    return ScriptDirectory.from_config(cfg or alembic_config()).get_current_head()


def current_revision(url: str | None = None) -> str | None:
    engine = create_engine(url or settings.database_url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def upgrade(url: str | None = None) -> None:
    url = url or settings.database_url
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            legacy = bool(tables) and "alembic_version" not in tables
            version = conn.exec_driver_sql("PRAGMA user_version").scalar() if conn.dialect.name == "sqlite" else None
    finally:
        engine.dispose()

    if legacy and version is not None and version < LEGACY_SCHEMA_VERSION:
        raise OutdatedDatabaseError(
            f"Die Datenbank ({url}) stammt von screenmates 0.1 und lässt sich nicht übernehmen. "
            "Datei umbenennen oder löschen, sie wird beim nächsten Start neu angelegt."
        )
    command.upgrade(alembic_config(url), "head")
