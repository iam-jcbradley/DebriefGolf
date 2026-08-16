from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.core.crypto import decrypt, encrypt


class GarminConnection(SQLModel, table=True):
    """A user's linked Garmin Connect account (PRD §4.1 OAuth 2.0 sync).

    One row per user — a fresh authorization overwrites the existing tokens
    rather than creating a second row (see app/api/routes/garmin_auth.py).

    The token columns hold ciphertext, not the tokens themselves (Phase 10,
    `app/core/crypto.py`). Go through `set_tokens()` and the
    `access_token`/`refresh_token` properties rather than touching the
    `*_encrypted` columns directly — the column names carry the `_encrypted`
    suffix precisely so that assigning a raw token to one looks wrong.
    """

    __tablename__ = "garmin_connection"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    access_token_encrypted: str = ""
    refresh_token_encrypted: str = ""
    token_type: str = "Bearer"
    scope: str | None = None
    expires_at: datetime
    connected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def set_tokens(self, access_token: str, refresh_token: str) -> None:
        self.access_token_encrypted = encrypt(access_token)
        self.refresh_token_encrypted = encrypt(refresh_token)

    @property
    def access_token(self) -> str | None:
        """None if SECRET_KEY was rotated after these were stored — see
        `app/core/crypto.py`. Callers should treat that as "reconnect
        needed", not as an error worth crashing a request over."""
        return decrypt(self.access_token_encrypted)

    @property
    def refresh_token(self) -> str | None:
        return decrypt(self.refresh_token_encrypted)
