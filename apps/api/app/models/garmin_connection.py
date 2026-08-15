from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class GarminConnection(SQLModel, table=True):
    """A user's linked Garmin Connect account (PRD §4.1 OAuth 2.0 sync).

    One row per user — a fresh authorization overwrites the existing tokens
    rather than creating a second row (see app/api/routes/garmin_auth.py).
    """

    __tablename__ = "garmin_connection"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    scope: str | None = None
    expires_at: datetime
    connected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
