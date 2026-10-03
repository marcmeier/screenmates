from collections.abc import Generator

from sqlalchemy import event, inspect
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        # SQLite ignores foreign keys (and therefore ON DELETE CASCADE) unless asked.
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()


# Bump when a model change can't be applied by `create_all` (new columns,
# changed constraints). There are no migrations yet, so an outdated SQLite file
# is refused with a clear message instead of failing later with SQL errors.
SCHEMA_VERSION = 2


class OutdatedDatabaseError(RuntimeError):
    pass


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    if _is_sqlite:
        with engine.connect() as conn:
            version = conn.exec_driver_sql("PRAGMA user_version").scalar()
            has_tables = bool(inspect(conn).get_table_names())
        if has_tables and version < SCHEMA_VERSION:
            raise OutdatedDatabaseError(
                f"Die Datenbank ({settings.database_url}) stammt von einer älteren screenmates-Version "
                f"(Schema {version}, benötigt {SCHEMA_VERSION}). Datei umbenennen oder löschen – "
                "sie wird beim nächsten Start neu angelegt."
            )
    SQLModel.metadata.create_all(engine)
    if _is_sqlite:
        with engine.begin() as conn:
            conn.exec_driver_sql(f"PRAGMA user_version = {SCHEMA_VERSION}")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
