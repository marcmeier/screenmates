"""Alembic environment for screenmates.

Two SQLite specifics matter here:

- Batch mode: SQLite can't ALTER most things, so Alembic rebuilds the table
  (copy, drop old, rename). `render_as_batch` makes autogenerate write that.
- Foreign keys OFF while migrating: the app turns them on for ON DELETE
  CASCADE. During a table rebuild that would turn "drop the old table" into
  "delete every child row", so migrations use their own connection without
  the app's pragma.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlmodel import SQLModel

from app import models  # noqa: F401  (registers the tables on SQLModel.metadata)
from app.config import settings

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata
url = config.attributes.get("url") or settings.database_url


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, render_as_batch=True, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url)  # deliberately without the app's foreign_keys=ON
    with engine.connect() as connection:
        if connection.dialect.name == "sqlite":
            # Must run outside a transaction (inside one SQLite ignores it), and
            # SQLAlchemy 2 auto-begins one here: commit it, or Alembic would see an
            # open transaction, not commit its own, and lose the version stamp.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
