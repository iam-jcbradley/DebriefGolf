from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import Column
from sqlmodel import Field, Relationship, SQLModel


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    city: str | None = None
    state: str | None = None
    # Set when this course was created from an OSM search result
    # (app/services/osm_courses.py) — lets re-searching the same course
    # resolve to the existing row instead of creating a duplicate.
    osm_relation_id: int | None = Field(default=None, index=True)

    holes: list["Hole"] = Relationship(back_populates="course")


class Hole(SQLModel, table=True):
    # WKTElement (below) has no Pydantic schema of its own — this table is
    # never validated against untrusted input (always constructed
    # internally with a real WKTElement), so there's nothing to validate.
    model_config = {"arbitrary_types_allowed": True}

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    number: int
    par: int
    yardage: int

    # Always written as a WKTElement (see app/api/routes/courses.py's
    # `_point`/`_polygon`, app/db/seed.py's `_point`) — never read back as
    # an attribute, since geoalchemy2 hands back a WKBElement instead (see
    # CLAUDE.md); every read goes through ST_Y/ST_X/ST_AsGeoJSON raw
    # columns. `str | None` was never the real type on either side.
    tee_location: WKTElement | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )
    green_center: WKTElement | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )
    green_boundary: WKTElement | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POLYGON", srid=4326))
    )

    course: Course = Relationship(back_populates="holes")
