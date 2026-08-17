"""Password hashing, login session tokens (PRD §9.2, Phase 10), and password
reset tokens (Phase 15).

Passwords are hashed with Argon2id (`argon2-cffi`, library defaults), the
current OWASP first choice for new applications — deliberately slow and
memory-hard, so a stolen `user.password_hash` column is expensive to attack
offline.

The session itself is a signed token (`app/core/signing.py`) carrying only a
user id and an expiry, delivered as an HttpOnly cookie. That keeps this app
free of server-side session storage, matching how the Garmin OAuth `state`
token already works. The trade-off is deliberate and worth stating: there is
no server-side revocation list, so a session token stays valid for its full
TTL even after "log out" (which clears the cookie) — rotating `SECRET_KEY`
is what invalidates every outstanding session at once. For a deployment this
size that's the right trade; a multi-tenant one would want session rows.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

from app.core.config import settings
from app.core.signing import TokenError, decode, encode

_hasher = PasswordHasher()

# Rejecting a too-short password is worth more than any complexity rule
# (mixed case, symbols) — those push people toward predictable substitutions
# without adding real entropy.
MIN_PASSWORD_LENGTH = 10


class WeakPasswordError(ValueError):
    pass


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """False rather than raising, for any reason the password doesn't match.

    `password_hash` may be None: users created before Phase 10 have no
    password set. Those accounts can't be logged into, which is the intended
    behaviour — see the phase notes in docs/DEVELOPMENT_PLAN.md.
    """
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except Argon2Error:
        return False


def create_session_token(user_id: int) -> str:
    return encode({"user_id": user_id}, ttl_seconds=settings.session_ttl_seconds)


def read_session_token(token: str) -> int | None:
    """The user id in `token`, or None if it isn't a valid, unexpired one."""
    try:
        payload = decode(token)
    except TokenError:
        return None
    user_id = payload.get("user_id")
    return user_id if isinstance(user_id, int) else None


# An hour comfortably outlasts checking email and clicking through, and
# bounds how long a leaked or intercepted reset link stays exploitable.
RESET_TOKEN_TTL_SECONDS = 60 * 60


def _password_fingerprint(password_hash: str | None) -> str:
    """A short fingerprint of the account's *current* password hash, bound
    into every reset token so it stops working the moment the password
    actually changes. There's no server-side token store to mark a token
    "used" (this app is deliberately stateless — see the module docstring),
    so binding to a value that the reset itself changes is what makes a
    token single-use: redeem it once, the hash moves, the same token no
    longer matches. `password_hash` may be None (a pre-Phase-10 account)
    — that's a valid, fingerprintable state, not a special case, which is
    exactly what lets those accounts recover through this same path.
    """
    basis = password_hash or "no-password-set"
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class ResetTokenPayload:
    user_id: int
    password_fingerprint: str


def create_reset_token(user_id: int, current_password_hash: str | None) -> str:
    return encode(
        {"user_id": user_id, "pwv": _password_fingerprint(current_password_hash)},
        ttl_seconds=RESET_TOKEN_TTL_SECONDS,
    )


def read_reset_token(token: str) -> ResetTokenPayload | None:
    """The token's payload if it's a validly-signed, unexpired reset token,
    else None. Doesn't check the fingerprint against a live user row — the
    caller has the database session and does that comparison itself (see
    `app/api/routes/auth.py::reset_password`), the same division of labor
    `read_session_token` already has with `get_current_user`.
    """
    try:
        payload = decode(token)
    except TokenError:
        return None
    user_id, pwv = payload.get("user_id"), payload.get("pwv")
    if not isinstance(user_id, int) or not isinstance(pwv, str):
        return None
    return ResetTokenPayload(user_id=user_id, password_fingerprint=pwv)


def reset_token_matches_current_password(
    user_password_hash: str | None, payload: ResetTokenPayload
) -> bool:
    """Whether `payload` (from `read_reset_token`) was minted against the
    account's password as it stands right now — false means either a stale
    concurrent reset request or a token that's already been redeemed once."""
    return _password_fingerprint(user_password_hash) == payload.password_fingerprint
