from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context
from app.core.config import settings
from app.models import (  # noqa: F401
    Course,
    GarminConnection,
    Hole,
    PracticeSession,
    PracticeShot,
    Round,
    Shot,
    StrokesGainedBenchmark,
    User,
    VirtualRound,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
#
# disable_existing_loggers=False: `fileConfig`'s default (True) disables
# every logger that already exists at this point — normally harmless, since
# `alembic upgrade head` runs as its own process. But `command.upgrade()`
# also runs in-process inside the test suite (tests/conftest.py, to build
# the throwaway test database) *after* `app.main` has already created and
# configured this app's own loggers (app/core/logging.py) — without this
# flag, that call silently disabled them (`Logger.disabled = True`) for the
# rest of the test session, with no error, just log lines that never
# appeared. Same guard uvicorn's own default logging config uses, and for
# the same reason.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# An explicitly-supplied URL wins over DATABASE_URL, so a caller driving
# alembic programmatically can migrate a database other than the configured
# one — `tests/conftest.py` uses this to build its own throwaway test
# database. Unset for ordinary CLI runs (`alembic upgrade head`), which keep
# using DATABASE_URL exactly as before.
config.set_main_option(
    "sqlalchemy.url", config.attributes.get("sqlalchemy_url") or settings.database_url
)

target_metadata = SQLModel.metadata

# The postgis/postgis image also installs postgis_topology and
# postgis_tiger_geocoder into the public schema, which litter it with
# tables we don't own. Only let autogenerate manage our own tables.
APP_TABLES = {table.name for table in SQLModel.metadata.tables.values()}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name not in APP_TABLES:
        return False
    return True

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
