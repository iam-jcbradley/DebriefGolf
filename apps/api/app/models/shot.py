from enum import StrEnum
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Column
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

    location: str | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )

    strokes_gained: float | None = None
    tag: str | None = None

    round: "Round" = Relationship(back_populates="shots")
