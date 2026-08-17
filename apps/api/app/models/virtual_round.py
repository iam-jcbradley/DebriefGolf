from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class SimPlatform(StrEnum):
    home_tee_hero = "home_tee_hero"
    e6 = "e6"
    gspro = "gspro"
    other = "other"


class VirtualRound(SQLModel, table=True):
    """A simulator round (PRD §6.2: Home Tee Hero, E6, GSPro) — deliberately
    a separate table from `Round`, not a `Round` subtype or a status flag on
    it. PRD §6.2 requires the Virtual/Sim Round Hub to be "segregated from
    real-world handicap calculations"; keeping it out of `Round` entirely
    means every existing handicap/analytics query that reads `Round` is
    correct by construction, with no `is_simulator` filter to remember to
    add. Scorecard-level only (no per-shot detail) — R10/R50 delivery data
    from a sim session, if any, is ingested separately as a `PracticeSession`
    and correlated by time/user, not by a foreign key to a specific virtual
    round.
    """

    __tablename__: str = "virtual_round"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    platform: SimPlatform
    course_name: str
    played_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    holes_played: int = 18
    total_score: int | None = None
    notes: str | None = None
