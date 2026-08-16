"""HMAC-signed, self-contained, expiring tokens.

Two features need to hand a small payload to a client and get it back
unforged without any server-side session storage: the Garmin OAuth `state`
parameter (`app/services/garmin_oauth.py`, which established this format in
Phase 3) and the login session cookie (`app/core/security.py`, Phase 10).
The mechanics are the same for both, so they live here rather than being
written twice.

Format: `b64url(json_payload).b64url(hmac_sha256(payload))`. The payload is
signed, not encrypted — it is readable by anyone holding the token, so don't
put anything secret in it. Every token carries its own `exp`, so a leaked one
stops working on its own.

The signing key is `settings.secret_key`, which the app refuses to boot with
at its default value outside development (see `app/core/config.py`).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import settings


class TokenError(Exception):
    """Base for every reason a token wasn't accepted."""


class MalformedToken(TokenError):
    pass


class BadSignature(TokenError):
    pass


class ExpiredToken(TokenError):
    pass


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def _sign(payload: bytes) -> str:
    return b64url_encode(
        hmac.new(settings.secret_key.encode(), payload, hashlib.sha256).digest()
    )


def encode(payload: dict[str, Any], ttl_seconds: int) -> str:
    """Signs `payload` with an expiry `ttl_seconds` from now."""
    body = json.dumps({**payload, "exp": time.time() + ttl_seconds}).encode()
    return f"{b64url_encode(body)}.{_sign(body)}"


def decode(token: str) -> dict[str, Any]:
    """Verifies signature and expiry, returning the payload.

    Raises `MalformedToken`, `BadSignature`, or `ExpiredToken` — callers
    that want a single message can catch `TokenError`.
    """
    try:
        body, signature = token.split(".", 1)
        payload = b64url_decode(body)
    except (ValueError, binascii.Error) as exc:
        raise MalformedToken("Malformed token") from exc

    # Constant-time: a timing-distinguishable comparison here would leak the
    # expected signature a byte at a time.
    if not hmac.compare_digest(_sign(payload), signature):
        raise BadSignature("Token signature mismatch")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise MalformedToken("Malformed token payload") from exc

    if not isinstance(data, dict) or "exp" not in data:
        raise MalformedToken("Malformed token payload")

    if data["exp"] < time.time():
        raise ExpiredToken("Token expired")

    return data
