from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import User
from app.services.garmin_oauth import build_authorize_request


def _seed_user(session: Session) -> int:
    user = User(email="garmin@example.com", name="Test User")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user.id


def _configure_garmin(monkeypatch) -> None:
    monkeypatch.setattr(settings, "garmin_client_id", "test-client-id")
    monkeypatch.setattr(settings, "garmin_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "garmin_authorize_url", "https://example.com/oauthConfirm")
    monkeypatch.setattr(settings, "garmin_token_url", "https://example.com/oauth/token")
    monkeypatch.setattr(
        settings, "garmin_redirect_uri", "http://localhost:8000/api/auth/garmin/callback"
    )
    monkeypatch.setattr(settings, "secret_key", "test-secret-key")


def _token_response(scope: str | None) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "at", "refresh_token": "rt",
        "token_type": "Bearer", "expires_in": 3600, "scope": scope,
    }
    return mock_response


def test_authorize_returns_url_when_configured(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    user_id = _seed_user(db_session)

    response = client.get(f"/api/auth/garmin/authorize?user_id={user_id}")

    assert response.status_code == 200
    assert response.json()["authorize_url"].startswith("https://example.com/oauthConfirm?")


def test_authorize_404_for_unknown_user(client: TestClient, monkeypatch) -> None:
    _configure_garmin(monkeypatch)
    response = client.get("/api/auth/garmin/authorize?user_id=999999")
    assert response.status_code == 404


def test_authorize_503_when_not_configured(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "garmin_client_id", "")
    user_id = _seed_user(db_session)

    response = client.get(f"/api/auth/garmin/authorize?user_id={user_id}")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_callback_creates_connection_and_redirects(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    user_id = _seed_user(db_session)
    request = build_authorize_request(user_id)

    with patch("httpx.AsyncClient.post", return_value=_token_response("ACTIVITY_EXPORT")):
        response = client.get(
            "/api/auth/garmin/callback",
            params={"code": "auth-code", "state": request.state},
            follow_redirects=False,
        )

    assert response.status_code in (302, 307)
    assert "connected=1" in response.headers["location"]

    status_response = client.get(f"/api/auth/garmin/{user_id}/status")
    assert status_response.json() == {"connected": True}


def test_callback_redirects_with_error_on_invalid_state(
    client: TestClient, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)

    response = client.get(
        "/api/auth/garmin/callback",
        params={"code": "auth-code", "state": "not-a-valid-state"},
        follow_redirects=False,
    )

    assert response.status_code in (302, 307)
    assert "error=" in response.headers["location"]


def test_status_false_when_not_connected(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    user_id = _seed_user(db_session)
    response = client.get(f"/api/auth/garmin/{user_id}/status")
    assert response.json() == {"connected": False}


def test_disconnect_removes_connection(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    user_id = _seed_user(db_session)
    request = build_authorize_request(user_id)

    with patch("httpx.AsyncClient.post", return_value=_token_response(None)):
        client.get(
            "/api/auth/garmin/callback",
            params={"code": "auth-code", "state": request.state},
            follow_redirects=False,
        )

    assert client.get(f"/api/auth/garmin/{user_id}/status").json() == {"connected": True}

    disconnect_response = client.delete(f"/api/auth/garmin/{user_id}")
    assert disconnect_response.json() == {"connected": False}
    assert client.get(f"/api/auth/garmin/{user_id}/status").json() == {"connected": False}


def test_disconnect_is_idempotent_when_never_connected(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    user_id = _seed_user(db_session)
    response = client.delete(f"/api/auth/garmin/{user_id}")
    assert response.status_code == 200
    assert response.json() == {"connected": False}
