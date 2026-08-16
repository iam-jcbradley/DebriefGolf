"""Shared test fixtures.

Route tests used to build `TestClient(app)` at import time and write through
the real `app.db.session.engine` — the developer's own database — with
nothing rolling back between tests. Two problems came out of that, and this
module fixes both.

**Tests leaked into each other.** The `uuid4()` email in every seed helper
existed to dodge collisions between tests that had already contaminated each
other. Each test now runs inside a transaction that is always rolled back, so
seeds can use fixed, readable values and no test can observe another's rows.
Two rules make that work:

1. The test's own seeding and the request under test must share one session.
   `client` binds `db_session` into the app through
   `app.dependency_overrides[get_session]`, so a row seeded in the test body
   is visible to the handler even though it was never committed.
2. Route handlers call `session.commit()` freely, and that has to keep
   working. `join_transaction_mode="create_savepoint"` (SQLAlchemy 2.0) makes
   each handler-level commit release a SAVEPOINT inside the outer transaction
   instead of ending it, so handlers behave exactly as they do in production
   while the fixture still gets to roll the whole thing back.

**Tests ran against the development database.** Rollback isolation doesn't
help against rows that were already there — `make seed` alone is enough to
break an assertion like "the search returns exactly one player". The suite now
provisions and migrates its own `<database>_test` database (override with
`TEST_DATABASE_URL`), so a developer's data and the suite can't break each
other in either direction.

Only tests that ask for `db_session`/`client` need any of this. The pure-logic
suites (parsers, strokes gained, geometry, combines) don't request them and
still run with no Postgres at all.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, create_engine, make_url, text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from alembic import command
from app.core.config import settings
from app.db.session import get_session
from app.main import app

API_ROOT = Path(__file__).resolve().parent.parent

_NO_DATABASE = """
Could not reach Postgres at {host}:{port} as user {user!r}.

The route tests need a real PostGIS server — the app's geometry columns have
no SQLite equivalent. Start one:

    make db-up

The test database itself ({database!r}) is created and migrated automatically;
it only needs a server to be running. Pure-logic tests (parsers, strokes
gained, geometry) need no database at all and can be run on their own:

    uv run pytest tests/parsers tests/test_geometry.py

Original error: {error}
"""

_NO_POSTGIS = """
Connected to {database!r}, but could not enable the PostGIS extension.

Creating it requires a superuser. The Docker Compose and CI databases both
connect as the bootstrap superuser, so this usually means the tests are
pointed at a hand-provisioned database via TEST_DATABASE_URL whose user has
fewer rights.

Original error: {error}
"""


def _test_database_url() -> URL:
    """`TEST_DATABASE_URL` if set, else the configured database with a
    `_test` suffix — never the development database itself."""
    override = os.environ.get("TEST_DATABASE_URL")
    if override:
        return make_url(override)
    configured = make_url(settings.database_url)
    return configured.set(database=f"{configured.database}_test")


def _create_database_if_missing(url: URL) -> None:
    # CREATE DATABASE can't run inside a transaction and can't run from a
    # connection to the database being created, so this goes through the
    # always-present `postgres` maintenance database in autocommit.
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            ).scalar()
            if not exists:
                # Identifiers can't be bound parameters. The name comes from
                # this repo's own configuration, not from user input.
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    except SQLAlchemyError as exc:
        pytest.fail(
            _NO_DATABASE.format(
                host=url.host, port=url.port, user=url.username, database=url.database, error=exc
            ),
            pytrace=False,
        )
    finally:
        admin_engine.dispose()


def _migrate(url: URL) -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    # Honoured by alembic/env.py in preference to DATABASE_URL.
    config.attributes["sqlalchemy_url"] = url.render_as_string(hide_password=False)
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def _engine() -> Iterator[Engine]:
    """Provisions, migrates, and hands back an engine for the test database.

    Session-scoped: the schema is built once per run, and per-test isolation
    comes from `db_session`'s rollback rather than from rebuilding it.
    """
    url = _test_database_url()
    _create_database_if_missing(url)

    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    except SQLAlchemyError as exc:
        engine.dispose()
        pytest.fail(_NO_POSTGIS.format(database=url.database, error=exc), pytrace=False)

    _migrate(url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(_engine: Engine) -> Iterator[Session]:
    """A session inside a transaction that is always rolled back."""
    connection = _engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """A `TestClient` whose handlers run against `db_session`, so requests
    and test-body seeding share one rolled-back transaction."""

    def _override_get_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
