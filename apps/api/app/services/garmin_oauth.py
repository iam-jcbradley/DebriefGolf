"""Garmin Connect OAuth 2.0 + PKCE plumbing (PRD §4.1, §9.2, §10 Phase 3).

This is a standard OAuth 2.0 Authorization Code + PKCE (RFC 7636) flow. It
cannot be exercised against Garmin's real servers in this environment — no
Garmin Developer Program credentials are available here, and the exact
authorize/token endpoint URLs must be filled in from Garmin's Developer
Portal docs (`GARMIN_AUTHORIZE_URL`, `GARMIN_TOKEN_URL` in `.env.example`).
Everything below is standard-conformant OAuth2 plumbing, unit-tested with a
mocked token endpoint — it needs real credentials and a live callback round
trip to verify against Garmin itself before shipping.

Flow:
1. `build_authorize_request(user_id)` generates a PKCE pair and a signed,
   self-contained `state` token (HMAC-signed, short-lived) carrying the
   user_id + code_verifier through the redirect — this app has no
   server-side session storage, so the state token stands in for one.
2. Garmin redirects back to `GARMIN_REDIRECT_URI` with `code` + `state`.
3. `decode_state(state)` verifies the signature/expiry and recovers
   `(user_id, code_verifier)`.
4. `exchange_code_for_token(code, code_verifier)` POSTs to Garmin's token
   endpoint and returns the access/refresh tokens to persist.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.signing import (
    BadSignature,
    ExpiredToken,
    MalformedToken,
    b64url_encode,
)
from app.core.signing import decode as decode_signed
from app.core.signing import encode as encode_signed

# Comfortably longer than a user takes to approve on Garmin's consent screen,
# short enough that a leaked/replayed state token doesn't stay valid long.
STATE_TTL_SECONDS = 600


class GarminOAuthError(Exception):
    pass


def _require_configured(*names: str) -> None:
    missing = [name for name in names if not getattr(settings, name)]
    if missing:
        raise GarminOAuthError(
            f"Garmin OAuth is not configured — missing: {', '.join(missing)}. "
            "Fill these in from the Garmin Developer Portal (see .env.example)."
        )


def generate_pkce_pair() -> tuple[str, str]:
    """Returns `(code_verifier, code_challenge)` for OAuth 2.0 PKCE, S256."""
    verifier = b64url_encode(secrets.token_bytes(32))
    challenge = b64url_encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def _encode_state(user_id: int, code_verifier: str) -> str:
    return encode_signed(
        {"user_id": user_id, "code_verifier": code_verifier}, ttl_seconds=STATE_TTL_SECONDS
    )


@dataclass(frozen=True)
class StatePayload:
    user_id: int
    code_verifier: str


def decode_state(state: str) -> StatePayload:
    # The signing/expiry mechanics moved to app/core/signing.py in Phase 10,
    # when the login session cookie needed the same thing. Only the wording
    # of the errors is specific to OAuth state.
    try:
        data = decode_signed(state)
    except BadSignature as exc:
        raise GarminOAuthError("State token signature mismatch") from exc
    except ExpiredToken as exc:
        raise GarminOAuthError("State token expired") from exc
    except MalformedToken as exc:
        raise GarminOAuthError("Malformed state token") from exc

    user_id, code_verifier = data.get("user_id"), data.get("code_verifier")
    if not isinstance(user_id, int) or not isinstance(code_verifier, str):
        raise GarminOAuthError("Malformed state token payload")

    return StatePayload(user_id=user_id, code_verifier=code_verifier)


@dataclass(frozen=True)
class AuthorizeRequest:
    url: str
    state: str


def build_authorize_request(user_id: int) -> AuthorizeRequest:
    _require_configured("garmin_client_id", "garmin_authorize_url", "garmin_redirect_uri")
    code_verifier, code_challenge = generate_pkce_pair()
    state = _encode_state(user_id, code_verifier)

    params = {
        "client_id": settings.garmin_client_id,
        "redirect_uri": settings.garmin_redirect_uri,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return AuthorizeRequest(url=f"{settings.garmin_authorize_url}?{urlencode(params)}", state=state)


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str | None


async def exchange_code_for_token(code: str, code_verifier: str) -> TokenResponse:
    _require_configured(
        "garmin_client_id", "garmin_client_secret", "garmin_token_url", "garmin_redirect_uri"
    )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.garmin_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.garmin_redirect_uri,
                "client_id": settings.garmin_client_id,
                "client_secret": settings.garmin_client_secret,
                "code_verifier": code_verifier,
            },
        )

    if response.status_code != 200:
        raise GarminOAuthError(
            f"Garmin token exchange failed: {response.status_code} {response.text}"
        )

    body = response.json()
    try:
        return TokenResponse(
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
            token_type=body.get("token_type", "Bearer"),
            expires_in=body["expires_in"],
            scope=body.get("scope"),
        )
    except KeyError as exc:
        raise GarminOAuthError(f"Garmin token response missing field: {exc}") from exc
