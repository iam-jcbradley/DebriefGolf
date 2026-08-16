"""Symmetric encryption for secrets this app stores on a user's behalf.

Currently just the Garmin OAuth access/refresh tokens (Phase 10). Those are
credentials for someone else's account, not data *about* the user — a
database dump that leaks them hands over live access to that person's Garmin
Connect account, which is worse than leaking any golf statistic in here. So
they're encrypted at rest rather than stored as the plain strings Phase 3
wrote.

Fernet (AES-128-CBC + HMAC-SHA256, authenticated) with a key derived from
`SECRET_KEY`. Deriving rather than configuring a second secret keeps
deployment to one thing to get right, at a stated cost: **rotating
SECRET_KEY makes existing stored tokens undecryptable**, and affected users
have to reconnect Garmin. That's an acceptable trade for a credential that
is re-obtainable by re-running the OAuth flow, and it's the same rotation
event that already invalidates every login session.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

# Domain separation: the same SECRET_KEY also signs session cookies and the
# OAuth state token. Hashing with a distinct label means the encryption key
# and the signing key are unrelated, so exposure of one doesn't imply the
# other.
_KEY_LABEL = b"debrief-golf/garmin-token-encryption/v1"


@lru_cache(maxsize=1)
def _fernet_for(secret_key: str) -> Fernet:
    digest = hashlib.sha256(_KEY_LABEL + secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _cipher() -> Fernet:
    # Keyed on the current secret so tests that monkeypatch `settings` get a
    # matching cipher instead of a stale cached one.
    return _fernet_for(settings.secret_key)


def encrypt(plaintext: str) -> str:
    return _cipher().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str | None:
    """The plaintext, or None if it can't be decrypted — which in practice
    means SECRET_KEY has been rotated since it was written. Callers treat
    that as "not connected" rather than crashing a request."""
    try:
        return _cipher().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None
