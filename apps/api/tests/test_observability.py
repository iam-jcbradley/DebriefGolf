"""Phase 12: request-id correlation and the catch-all exception handler."""

import logging
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.session import get_session
from app.main import app


@pytest.fixture
def unsafe_client(db_session: Session) -> Iterator[TestClient]:
    """Like the shared `client` fixture, but with `raise_server_exceptions=
    False`: the ordinary `client` fixture re-raises an unhandled exception
    straight into the test (useful everywhere else, to surface a real bug
    loudly) — exactly the behavior these tests need to see past, to assert
    on the *response* `unhandled_exception_handler` actually produces."""

    def _override_get_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert uuid.UUID(request_id)  # well-formed, doesn't raise


def test_different_requests_get_different_request_ids(client: TestClient) -> None:
    first = client.get("/api/health").headers["x-request-id"]
    second = client.get("/api/health").headers["x-request-id"]

    assert first != second


class TestUnhandledException:
    """Forces `get_session` (already overridden by the `client` fixture) to
    raise, so a real endpoint hits the catch-all handler for real — not a
    handcrafted Request/exc pair that might not match what Starlette
    actually passes it."""

    def test_returns_a_clean_500_with_no_traceback_in_the_body(
        self, unsafe_client: TestClient
    ) -> None:
        def _boom():
            raise RuntimeError("the database is on fire")
            yield  # pragma: no cover - makes this a generator, matching get_session's shape

        unsafe_client.app.dependency_overrides[get_session] = _boom

        response = unsafe_client.get("/api/ready")

        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Internal server error"
        assert "the database is on fire" not in response.text
        assert "Traceback" not in response.text

    def test_response_request_id_matches_the_logged_one(
        self, unsafe_client: TestClient, caplog
    ) -> None:
        def _boom():
            raise RuntimeError("boom")
            yield  # pragma: no cover

        unsafe_client.app.dependency_overrides[get_session] = _boom

        with caplog.at_level(logging.ERROR, logger="app.request"):
            response = unsafe_client.get("/api/ready")

        request_id = response.json()["request_id"]
        assert request_id == response.headers["x-request-id"]
        assert any(
            getattr(record, "request_id", None) == request_id and record.exc_info
            for record in caplog.records
        )
