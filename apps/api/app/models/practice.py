from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel


class PracticeSession(SQLModel, table=True):
    """One R10/R50 launch-monitor export (PRD §6.1, §10 Phase 6) — a batch of
    `PracticeShot` rows parsed by `app.services.parsers.launch_monitor_parser`
    and attributed to a user. `source` is free text (e.g. "R10", "R50")
    rather than an enum: Garmin doesn't publish a fixed device list in the
    export itself, matching the header-alias tolerance the parser already
    has.
    """

    __tablename__ = "practice_session"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    source: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    shots: list["PracticeShot"] = Relationship(back_populates="session")


class PracticeShot(SQLModel, table=True):
    """One delivered ball flight from an R10/R50 export
    (`app.services.parsers.launch_monitor_parser.LaunchMonitorShot`,
    persisted). Face-to-path is derived at read time (face_angle_deg -
    club_path_deg) rather than stored, since it's a pure function of the two
    columns already here."""

    __tablename__ = "practice_shot"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="practice_session.id", index=True, ondelete="CASCADE")
    club: str = Field(index=True)
    club_speed_mph: float | None = None
    ball_speed_mph: float | None = None
    smash_factor: float | None = None
    launch_angle_deg: float | None = None
    spin_rate_rpm: float | None = None
    spin_axis_deg: float | None = None
    club_path_deg: float | None = None
    face_angle_deg: float | None = None
    carry_yards: float | None = None
    total_yards: float | None = None
    captured_at: datetime | None = None

    session: "PracticeSession" = Relationship(back_populates="shots")
