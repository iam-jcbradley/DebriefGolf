"""Password hashing and login session tokens (PRD §9.2, Phase 10).

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
