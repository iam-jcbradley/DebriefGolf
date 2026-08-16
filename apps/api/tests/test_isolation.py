"""Tests for the test harness itself (`conftest.py`).

Per-test isolation is the kind of guarantee that fails silently: the suite
goes green either way, and the damage only shows up later as a test that
passes alone and fails in a full run. These assert the two properties the
rest of the suite now relies on.
"""

from fastapi.testclient import TestClient
from sqlalchemy import Engine, make_url
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User

# Deliberately shared between the two tests below. `user.email` is unique,
# so if the first test's committed row outlived its transaction, the second
# would get a 409 instead of a 201.
PROBE_EMAIL = "isolation-probe@example.com"


def test_a_commits_a_user(client: TestClient) -> None:
    response = client.post("/api/users", json={"name": "Probe", "email": PROBE_EMAIL})
    assert response.status_code == 201


def test_b_does_not_see_the_user_committed_by_test_a(
    client: TestClient, db_session: Session
) -> None:
    response = client.post("/api/users", json={"name": "Probe", "email": PROBE_EMAIL})

    assert response.status_code == 201, "test_a's committed row leaked out of its transaction"
    assert len(db_session.exec(select(User).where(User.email == PROBE_EMAIL)).all()) == 1


def test_handler_commits_are_visible_to_the_test_body(
    client: TestClient, db_session: Session
) -> None:
    """The other half of the contract: rolling everything back at the end
    must not stop a handler's `session.commit()` from taking effect *during*
    the test, or route tests couldn't assert on what a request persisted."""
    created = client.post(
        "/api/users", json={"name": "Committed", "email": "commit-probe@example.com"}
    ).json()

    assert db_session.get(User, created["id"]) is not None


def test_suite_does_not_run_against_the_development_database(_engine: Engine) -> None:
    assert _engine.url.database != make_url(settings.database_url).database
