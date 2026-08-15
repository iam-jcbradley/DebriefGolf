from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    handicap_index: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
