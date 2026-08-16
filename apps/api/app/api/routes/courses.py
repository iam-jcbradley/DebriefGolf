import json

from fastapi import APIRouter, HTTPException, Response
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Course, Hole
from app.services.osm_courses import (
    OsmLookupError,
    fetch_course_geometry,
    search_courses,
)

router = APIRouter()


class LatLngIn(BaseModel):
    lat: float
    lng: float


class HoleCreateIn(BaseModel):
    number: int
    par: int
    yardage: int
    tee_location: LatLngIn | None = None
    green_center: LatLngIn | None = None
    # Polygon ring, in order; need not repeat the first point as the last.
    green_boundary: list[LatLngIn] | None = None


class CourseCreateIn(BaseModel):
    name: str
    city: str | None = None
    state: str | None = None
    osm_relation_id: int | None = None
    holes: list[HoleCreateIn] = []


def _point(p: LatLngIn) -> WKTElement:
    return WKTElement(f"POINT({p.lng} {p.lat})", srid=4326)


def _polygon(points: list[LatLngIn]) -> WKTElement:
    ring = list(points)
    if ring[0].lat != ring[-1].lat or ring[0].lng != ring[-1].lng:
        ring.append(ring[0])
    coords = ", ".join(f"{p.lng} {p.lat}" for p in ring)
    return WKTElement(f"POLYGON(({coords}))", srid=4326)


def _serialize_course(session: Session, course: Course) -> dict:
    holes = session.exec(
        select(Hole).where(Hole.course_id == course.id).order_by(Hole.number)
    ).all()

    geo_by_hole: dict[int, dict] = {}
    hole_ids = [hole.id for hole in holes]
    if hole_ids:
        rows = session.exec(
            select(
                Hole.id,
                func.ST_Y(Hole.tee_location).label("tee_lat"),
                func.ST_X(Hole.tee_location).label("tee_lng"),
                func.ST_Y(Hole.green_center).label("green_lat"),
                func.ST_X(Hole.green_center).label("green_lng"),
                func.ST_AsGeoJSON(Hole.green_boundary).label("green_boundary_geojson"),
            ).where(Hole.id.in_(hole_ids))
        ).all()
        for row in rows:
            boundary = None
            if row.green_boundary_geojson:
                ring = json.loads(row.green_boundary_geojson)["coordinates"][0]
                boundary = [{"lat": lat, "lng": lng} for lng, lat in ring]
            geo_by_hole[row.id] = {
                "tee": (
                    {"lat": row.tee_lat, "lng": row.tee_lng} if row.tee_lat is not None else None
                ),
                "green_center": (
                    {"lat": row.green_lat, "lng": row.green_lng}
                    if row.green_lat is not None
                    else None
                ),
                "green_boundary": boundary,
            }

    empty_geo = {"tee": None, "green_center": None, "green_boundary": None}
    return {
        "id": course.id,
        "name": course.name,
        "city": course.city,
        "state": course.state,
        "osm_relation_id": course.osm_relation_id,
        "holes": [
            {
                "hole_number": hole.number,
                "par": hole.par,
                "yardage": hole.yardage,
                **geo_by_hole.get(hole.id, empty_geo),
            }
            for hole in holes
        ],
    }


# Courses are shared reference data rather than per-user data, so none of
# these are scoped to the caller — but they all still require a session.
# `POST /courses` writes data every user's rounds can reference, and the
# search endpoints proxy OpenStreetMap's public Overpass API; neither is
# something to leave open to anonymous callers.
@router.get("/courses")
def list_courses(user: CurrentUser, session: SessionDep) -> list[dict]:
    """Course picker list (name/city/state only — fetch /courses/{id} for
    hole geometry)."""
    courses = session.exec(select(Course).order_by(Course.name)).all()
    return [{"id": c.id, "name": c.name, "city": c.city, "state": c.state} for c in courses]


@router.get("/courses/search-osm")
async def search_osm(q: str, user: CurrentUser) -> list[dict]:
    """Search OpenStreetMap for a course by name (`app/services/osm_courses.py`)
    — a free alternative to hand-placing every point when a course is
    already mapped there. See that module's docstring for coverage caveats
    and this-environment verification limits."""
    try:
        results = await search_courses(q)
    except OsmLookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [
        {
            "osm_type": r.osm_type,
            "osm_id": r.osm_id,
            "name": r.name,
            "city": r.city,
            "state": r.state,
            "center": {"lat": r.center.lat, "lng": r.center.lng} if r.center else None,
        }
        for r in results
    ]


@router.get("/courses/search-osm/{osm_type}/{osm_id}")
async def search_osm_geometry(osm_type: str, osm_id: int, user: CurrentUser) -> dict:
    """Fetches hole/tee/green geometry for one OSM search result. Returned
    in a draft shape close to `CourseCreateIn` — the frontend lets the user
    review/fill gaps (missing par, unmatched tee/green, etc.) before
    submitting to `POST /courses`, since OSM coverage is inconsistent."""
    if osm_type not in ("way", "relation", "node"):
        raise HTTPException(status_code=422, detail="osm_type must be way, relation, or node")
    try:
        detail = await fetch_course_geometry(osm_type, osm_id)
    except OsmLookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "name": detail.name,
        "city": detail.city,
        "state": detail.state,
        "osm_relation_id": detail.osm_id,
        "holes": [
            {
                "number": h.number,
                "par": h.par,
                "yardage": h.yardage,
                "tee_location": {"lat": h.tee_location.lat, "lng": h.tee_location.lng}
                if h.tee_location
                else None,
                "green_center": {"lat": h.green_center.lat, "lng": h.green_center.lng}
                if h.green_center
                else None,
                "green_boundary": [{"lat": p.lat, "lng": p.lng} for p in h.green_boundary]
                if h.green_boundary
                else None,
            }
            for h in detail.holes
        ],
    }


@router.get("/courses/{course_id}")
def get_course(course_id: int, user: CurrentUser, session: SessionDep) -> dict:
    course = session.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return _serialize_course(session, course)


@router.post("/courses", status_code=201)
def create_course(
    payload: CourseCreateIn,
    response: Response,
    user: CurrentUser,
    session: SessionDep,
) -> dict:
    """Manual course creation (PRD §10 Phase 5): a user builds a course by
    hand — or from a reviewed/edited `GET /courses/search-osm` candidate —
    since Garmin's OAuth API (Phase 3) turned out to require a paid
    developer account and can't be relied on to supply course data.

    Idempotent on `osm_relation_id`: re-submitting a course sourced from the
    same OSM relation returns the existing row instead of duplicating it.
    """
    numbers = [h.number for h in payload.holes]
    if len(numbers) != len(set(numbers)):
        raise HTTPException(status_code=422, detail="Hole numbers must be unique")

    if payload.osm_relation_id is not None:
        existing = session.exec(
            select(Course).where(Course.osm_relation_id == payload.osm_relation_id)
        ).first()
        if existing:
            response.status_code = 200
            return _serialize_course(session, existing)

    course = Course(
        name=payload.name,
        city=payload.city,
        state=payload.state,
        osm_relation_id=payload.osm_relation_id,
    )
    session.add(course)
    session.commit()
    session.refresh(course)

    for h in payload.holes:
        session.add(
            Hole(
                course_id=course.id,
                number=h.number,
                par=h.par,
                yardage=h.yardage,
                tee_location=_point(h.tee_location) if h.tee_location else None,
                green_center=_point(h.green_center) if h.green_center else None,
                green_boundary=(
                    _polygon(h.green_boundary)
                    if h.green_boundary and len(h.green_boundary) >= 3
                    else None
                ),
            )
        )
    session.commit()

    return _serialize_course(session, course)
