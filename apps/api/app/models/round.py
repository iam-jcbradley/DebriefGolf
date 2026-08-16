from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.shot import Shot


class RoundStatus(StrEnum):
    verified = "verified"
    needs_audit = "needs_audit"
    casual_practice = "casual_practice"


class Round(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    # Nullable: a freshly-uploaded .FIT activity (app/services/parsers/fit_parser.py)
    # has GPS points but no matched course yet — course-matching (GPS bounding
    # box -> Course) is its own feature, not built. The audit wizard (Phase 3)
    # is where a user would confirm/assign the course.
    course_id: int | None = Field(default=None, foreign_key="course.id")
    played_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_score: int | None = None
    status: RoundStatus = Field(default=RoundStatus.needs_audit)

    shots: list["Shot"] = Relationship(back_populates="round")
