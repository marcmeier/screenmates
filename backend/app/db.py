from collections.abc import Generator

from sqlalchemy import event
from sqlmodel import Session, create_engine

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Many open apps poll at once (live, Kino, chat); a SQLite connection is cheap.
    **({"pool_size": 20, "max_overflow": 40} if _is_sqlite else {}),
)


def freigeben(db: Session) -> None:
    """Give the connection back before waiting on something slow (MediaMTX, TMDB, the LLM).

    A session keeps its connection until the transaction ends; an endpoint that
    awaits the network meanwhile would hold it for seconds. The next query simply
    takes a connection again.
    """
    db.commit()


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        # SQLite ignores foreign keys (and therefore ON DELETE CASCADE) unless asked.
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()


def init_db() -> None:
    """Migrate to the newest schema (see app/migrate.py)."""
    from . import migrate, models  # noqa: F401  (register tables)

    migrate.upgrade()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
