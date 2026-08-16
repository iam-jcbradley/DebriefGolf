from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models import User
from app.services.garmin_oauth import build_authorize_request


def _configure_garmin(monkeypatch) -> None:
    monkeypatch.setattr(settings, "garmin_client_id", "test-client-id")
    monkeypatch.setattr(settings, "garmin_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "garmin_authorize_url", "https://example.com/oauthConfirm")
    monkeypatch.setattr(settings, "garmin_token_url", "https://example.com/oauth/token")
    monkeypatch.setattr(
        settings, "garmin_redirect_uri", "http://localhost:8000/api/auth/garmin/callback"
    )
    # Deliberately does NOT monkeypatch `secret_key`, unlike the unit tests
    # in test_garmin_oauth.py. That key signs the session cookie too, so
    # changing it mid-test invalidates the login `auth_client` already
    # performed and every request here 401s — the same rotation behaviour
    # described in app/core/security.py, arrived at the hard way.


def _token_response(scope: str | None) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "at", "refresh_token": "rt",
        "token_type": "Bearer", "expires_in": 3600, "scope": scope,
    }
    return mock_response


def test_authorize_returns_url_when_configured(auth_client: TestClient, monkeypatch) -> None:
    _configure_garmin(monkeypatch)

    response = auth_client.get("/api/auth/garmin/authorize")

    assert response.status_code == 200
    assert response.json()["authorize_url"].startswith("https://example.com/oauthConfirm?")


def test_authorize_503_when_not_configured(auth_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "garmin_client_id", "")

    response = auth_client.get("/api/auth/garmin/authorize")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_callback_creates_connection_and_redirects(
    auth_client: TestClient, user: User, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    request = build_authorize_request(user.id)

    with patch("httpx.AsyncClient.post", return_value=_token_response("ACTIVITY_EXPORT")):
        response = auth_client.get(
            "/api/auth/garmin/callback",
            params={"code": "auth-code", "state": request.state},
            follow_redirects=False,
        )

    assert response.status_code in (302, 307)
    assert "connected=1" in response.headers["location"]

    status_response = auth_client.get("/api/auth/garmin/status")
    assert status_response.json() == {"connected": True}


def test_callback_redirects_with_error_on_invalid_state(
    client: TestClient, monkeypatch
) -> None:
    # No session needed: Garmin's redirect is authorized by the signed
    # `state` token, not by a cookie.
    _configure_garmin(monkeypatch)

    response = client.get(
        "/api/auth/garmin/callback",
        params={"code": "auth-code", "state": "not-a-valid-state"},
        follow_redirects=False,
    )

    assert response.status_code in (302, 307)
    assert "error=" in response.headers["location"]


def test_status_false_when_not_connected(auth_client: TestClient, monkeypatch) -> None:
    _configure_garmin(monkeypatch)
    response = auth_client.get("/api/auth/garmin/status")
    assert response.json() == {"connected": False}


def test_disconnect_removes_connection(
    auth_client: TestClient, user: User, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    request = build_authorize_request(user.id)

    with patch("httpx.AsyncClient.post", return_value=_token_response(None)):
        auth_client.get(
            "/api/auth/garmin/callback",
            params={"code": "auth-code", "state": request.state},
            follow_redirects=False,
        )

    assert auth_client.get("/api/auth/garmin/status").json() == {"connected": True}

    disconnect_response = auth_client.delete("/api/auth/garmin")
    assert disconnect_response.json() == {"connected": False}
    assert auth_client.get("/api/auth/garmin/status").json() == {"connected": False}


def test_disconnect_is_idempotent_when_never_connected(
    auth_client: TestClient, monkeypatch
) -> None:
    _configure_garmin(monkeypatch)
    response = auth_client.delete("/api/auth/garmin")
    assert response.status_code == 200
    assert response.json() == {"connected": False}
