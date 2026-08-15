from geoalchemy2 import Geometry
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
    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id")
    number: int
    par: int
    yardage: int

    tee_location: str | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )
    green_center: str | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )
    green_boundary: str | None = Field(
        default=None, sa_column=Column(Geometry(geometry_type="POLYGON", srid=4326))
    )

    course: Course = Relationship(back_populates="holes")
