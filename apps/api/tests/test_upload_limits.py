"""Upload size limits (Phase 11).

Both endpoints used to `await file.read()` the whole request body into
memory with no cap, so a single large upload could take the API process
with it.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.uploads import MAX_UPLOAD_BYTES

UPLOAD_ENDPOINTS = [
    ("/api/rounds/upload", "round.fit"),
    ("/api/practice/sessions/upload?source=R10", "session.csv"),
]


@pytest.mark.parametrize(("path", "filename"), UPLOAD_ENDPOINTS)
def test_rejects_a_file_over_the_limit(
    auth_client: TestClient, path: str, filename: str
) -> None:
    oversized = b"x" * (MAX_UPLOAD_BYTES + 1)

    response = auth_client.post(
        path, files={"file": (filename, oversized, "application/octet-stream")}
    )

    assert response.status_code == 413
    assert "limit" in response.json()["detail"]


@pytest.mark.parametrize(("path", "filename"), UPLOAD_ENDPOINTS)
def test_rejects_before_the_body_is_parsed(
    auth_client: TestClient, path: str, filename: str
) -> None:
    """The middleware refuses on `Content-Length` alone, before routing.

    Proven by the response arriving without a session: the endpoints require
    one, so a 413 (rather than the 401 an unauthenticated caller would
    otherwise get) means nothing downstream of the middleware ran — which is
    the point, since by the time a handler executes the multipart body has
    already been parsed and spooled to disk.
    """
    auth_client.cookies.clear()
    oversized = b"x" * (MAX_UPLOAD_BYTES + 1)

    response = auth_client.post(
        path, files={"file": (filename, oversized, "application/octet-stream")}
    )

    assert response.status_code == 413


def test_accepts_a_file_within_the_limit(auth_client: TestClient) -> None:
    """The cap must not reject ordinary uploads. A corrupted .FIT still
    creates a round flagged casual_practice (PRD §4.3), which is the
    behaviour being preserved here — the point is that it isn't a 413."""
    response = auth_client.post(
        "/api/rounds/upload",
        files={"file": ("round.fit", b"y" * 1024, "application/octet-stream")},
    )

    assert response.status_code == 200
