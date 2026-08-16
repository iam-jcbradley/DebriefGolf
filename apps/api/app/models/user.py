from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    handicap_index: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Argon2id (app/core/security.py). Nullable because accounts created
    # before Phase 10 introduced login have none — `verify_password` treats
    # that as "can't log in" rather than "no password required".
    #
    # Never serialize this. Routes return explicit response models rather
    # than the `User` row for exactly this reason (see app/api/routes/auth.py).
    password_hash: str | None = Field(default=None)
