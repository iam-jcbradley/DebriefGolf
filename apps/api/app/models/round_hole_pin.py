from geoalchemy2 import Geometry
from sqlalchemy import Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class RoundHolePin(SQLModel, table=True):
    """Where the pin actually was, for one hole, on one round (Phase 14).

    Deliberately not a column on `Hole` — that table is shared reference
    geometry across every user's round on that hole, and a pin is a
    property of one round on one day, the same reasoning that keeps
    `VirtualRound` separate from `Round`. `hole_id` has no cascade, matching
    `Shot.hole_id`'s own comment: a `Hole` isn't this row's to own. One pin
    per hole per round — a second placement replaces it (see
    `POST /rounds/{id}/pins/bulk`), it doesn't create a second row.
    """

    __tablename__ = "round_hole_pin"
    __table_args__ = (UniqueConstraint("round_id", "hole_id", name="uq_pin_round_hole"),)

    id: int | None = Field(default=None, primary_key=True)
    round_id: int = Field(foreign_key="round.id", index=True, ondelete="CASCADE")
    hole_id: int = Field(foreign_key="hole.id", index=True)

    # A plain (Optional-less) type hint isn't enough to make this NOT NULL
    # once a custom sa_column is supplied — SQLModel only infers nullability
    # from the annotation when it builds the Column itself.
    location: str = Field(
        sa_column=Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    )
