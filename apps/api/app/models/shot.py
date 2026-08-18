from enum import StrEnum
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.round import Round


class Lie(StrEnum):
    tee = "tee"
    fairway = "fairway"
    rough = "rough"
    sand = "sand"
    recovery = "recovery"
    green = "green"
    fringe = "fringe"
    penalty = "penalty"
    hole = "hole"


class Shot(SQLModel, table=True):
    # A hole's shot 1, shot 2, ... is a natural key, not just a dedup
    # mechanism — two different shots can't both be "shot #2 of hole #5 of
    # this round". Enforced at the DB level (not just app-level checking) so
    # `POST /rounds/{id}/shots/bulk` retried after a dropped connection
    # can't silently duplicate a hole's shots; see that route for how a
    # collision is handled (the existing shot wins, not an error).
    __table_args__ = (
        UniqueConstraint("round_id", "hole_id", "shot_number", name="uq_shot_round_hole_number"),
    )
    # WKTElement (location, below) has no Pydantic schema of its own — this
    # table is never validated against untrusted input (always constructed
    # internally with a real WKTElement), so there's nothing to validate.
    model_config = {"arbitrary_types_allowed": True}

    id: int | None = Field(default=None, primary_key=True)
    round_id: int = Field(foreign_key="round.id", index=True, ondelete="CASCADE")
    # No cascade: a Hole is shared reference geometry, not this shot's to own.
    hole_id: int = Field(foreign_key="hole.id", index=True)
    shot_number: int

    club: str | None = None
    start_lie: Lie
    end_lie: Lie
    start_distance_yards: float
    end_distance_yards: float

    # Always written as a WKTElement, never read back as an attribute — see
    # app/models/course.py's geometry fields for why `str | None` was wrong.
    location: WKTElement | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )

    strokes_gained: float | None = None
    tag: str | None = None

    round: "Round" = Relationship(back_populates="shots")
