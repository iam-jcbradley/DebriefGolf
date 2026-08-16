import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.garmin_oauth import (
    GarminOAuthError,
    build_authorize_request,
    decode_state,
    exchange_code_for_token,
    generate_pkce_pair,
)


@pytest.fixture(autouse=True)
def _configured_garmin_settings(monkeypatch):
    monkeypatch.setattr(settings, "garmin_client_id", "test-client-id")
    monkeypatch.setattr(settings, "garmin_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "garmin_authorize_url", "https://example.com/oauthConfirm")
    monkeypatch.setattr(settings, "garmin_token_url", "https://example.com/oauth/token")
    monkeypatch.setattr(settings, "garmin_redirect_uri", "http://localhost:8000/api/auth/garmin/callback")
    monkeypatch.setattr(settings, "secret_key", "test-secret-key")


def test_generate_pkce_pair_challenge_matches_sha256_of_verifier() -> None:
    import base64
    import hashlib

    verifier, challenge = generate_pkce_pair()
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    assert challenge == expected_challenge
    assert "=" not in verifier
    assert "=" not in challenge


def test_generate_pkce_pair_is_random_each_call() -> None:
    verifier1, _ = generate_pkce_pair()
    verifier2, _ = generate_pkce_pair()
    assert verifier1 != verifier2


class TestState:
    def test_state_round_trips_user_id_and_code_verifier(self) -> None:
        request = build_authorize_request(user_id=42)
        payload = decode_state(request.state)
        assert payload.user_id == 42
        assert payload.code_verifier

    def test_tampered_state_is_rejected(self) -> None:
        request = build_authorize_request(user_id=42)
        tampered = request.state[:-1] + ("A" if request.state[-1] != "A" else "B")
        with pytest.raises(GarminOAuthError, match="signature"):
            decode_state(tampered)

    def test_malformed_state_is_rejected(self) -> None:
        with pytest.raises(GarminOAuthError, match="Malformed"):
            decode_state("not-a-valid-state-token")

    def test_expired_state_is_rejected(self) -> None:
        request = build_authorize_request(user_id=42)
        # The clock lives in app/core/signing.py since Phase 10 — the state
        # token's signing/expiry mechanics are shared with session cookies.
        with patch("app.core.signing.time.time", return_value=time.time() + 10_000):
            with pytest.raises(GarminOAuthError, match="expired"):
                decode_state(request.state)


class TestBuildAuthorizeRequest:
    def test_url_includes_pkce_and_client_params(self) -> None:
        request = build_authorize_request(user_id=1)
        assert request.url.startswith("https://example.com/oauthConfirm?")
        assert "client_id=test-client-id" in request.url
        assert "code_challenge=" in request.url
        assert "code_challenge_method=S256" in request.url
        assert f"state={request.state}" in request.url.replace("%2E", ".")

    def test_raises_clearly_when_not_configured(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "garmin_client_id", "")
        with pytest.raises(GarminOAuthError, match="garmin_client_id"):
            build_authorize_request(user_id=1)


class TestExchangeCodeForToken:
    def test_successful_exchange_returns_token_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "at",
            "refresh_token": "rt",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "ACTIVITY_EXPORT",
        }
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            token = asyncio.run(exchange_code_for_token("auth-code", "verifier"))

        assert token.access_token == "at"
        assert token.refresh_token == "rt"
        assert token.expires_in == 3600

    def test_non_200_response_raises(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "invalid_grant"
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with pytest.raises(GarminOAuthError, match="400"):
                asyncio.run(exchange_code_for_token("bad-code", "verifier"))

    def test_missing_field_in_response_raises(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "at"}  # missing other fields
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with pytest.raises(GarminOAuthError, match="missing field"):
                asyncio.run(exchange_code_for_token("auth-code", "verifier"))

    def test_raises_clearly_when_not_configured(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "garmin_client_secret", "")
        with pytest.raises(GarminOAuthError, match="garmin_client_secret"):
            asyncio.run(exchange_code_for_token("auth-code", "verifier"))
