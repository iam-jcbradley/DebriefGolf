"""OpenStreetMap course/hole geometry lookup (PRD §10 Phase 5).

Garmin's Developer Program turned out to require a paid account (discovered
after Phase 3 shipped OAuth plumbing against it) — auto-syncing rounds isn't
viable for ordinary users, so course/round/shot data now has to be entered
by hand while looking at another app (e.g. Garmin Golf's own shot map).
Requiring every user to hand-place a course's tee/green/boundary points from
scratch on top of that would be a lot of tedious, error-prone work, so this
searches OpenStreetMap's Overpass API (free, keyless, public — no account or
billing risk, unlike Garmin's or a commercial golf-course API) for a course
by name and prefills whatever geometry it has mapped.

OSM's golf tagging scheme (see the OSM wiki's Golf project page): a course
is `leisure=golf_course`; each hole is a `golf=hole` way tracing its
centerline, tagged `ref` (hole number) and sometimes `par`; tee boxes and
greens are separate `golf=tee`/`golf=green` features, not explicitly linked
to their hole by any relation membership in most mappings. This resolves
that link with a nearest-endpoint heuristic: a hole's first/last centerline
points are matched to the closest tee/green feature within
`_MAX_MATCH_DISTANCE_YARDS`, using the same flat-earth yard-distance
(`app/services/geometry.py`) the rest of the app already uses for hole
geometry. Coverage is inconsistent — well-known public courses tend to be
well-mapped, private/smaller clubs sometimes aren't mapped at all, and `par`
is frequently missing — so every field here is optional and this always
degrades to "the user fills in the gaps by hand" (`POST /api/courses`)
rather than failing outright.

**Unverified against the real Overpass API in this environment** — outbound
requests to overpass-api.de are blocked by this sandbox's network egress
policy (confirmed via the proxy status endpoint: "gateway answered 403 to
CONNECT"), same boundary as Phase 3's Garmin OAuth and Phase 4's Mapbox
integration. The query construction and response parsing below are unit
tested against hand-built fixtures shaped like real Overpass JSON output
(`tests/test_osm_courses.py`), not a live round trip.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import httpx

from app.services.geometry import LatLng, local_yards

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_TIMEOUT_SECONDS = 25.0
_MAX_SEARCH_RESULTS = 10
# Beyond this, a tee/green feature isn't considered a match for a hole's
# endpoint — an unmatched endpoint is left unset rather than guessed.
_MAX_MATCH_DISTANCE_YARDS = 80.0


class OsmLookupError(Exception):
    pass


@dataclass(frozen=True)
class OsmCourseSummary:
    """One name-search result — enough to let the user pick a course before
    fetching its (potentially large) hole geometry. `center` lets a map
    center itself on the course before any hole geometry has been fetched
    or built."""

    osm_type: str  # "way" | "relation" | "node"
    osm_id: int
    name: str
    city: str | None
    state: str | None
    center: LatLng | None


@dataclass(frozen=True)
class OsmHoleCandidate:
    number: int | None
    par: int | None
    yardage: int | None  # computed from the hole way's own geometry, when present
    tee_location: LatLng | None
    green_center: LatLng | None
    green_boundary: list[LatLng] | None


@dataclass(frozen=True)
class OsmCourseDetail:
    osm_id: int
    name: str
    city: str | None
    state: str | None
    holes: list[OsmHoleCandidate]


def _escape_overpass_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def _run_query(ql: str) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        try:
            response = await client.post(OVERPASS_URL, data={"data": ql})
        except httpx.HTTPError as exc:
            raise OsmLookupError(f"Overpass request failed: {exc}") from exc

    if response.status_code != 200:
        raise OsmLookupError(f"Overpass returned {response.status_code}: {response.text[:200]}")
    return response.json()


async def search_courses(query: str) -> list[OsmCourseSummary]:
    """Searches OSM for golf courses whose `name` contains `query`
    (case-insensitive)."""
    escaped = _escape_overpass_string(query)
    ql = (
        "[out:json][timeout:25];"
        f'nwr["leisure"="golf_course"]["name"~"{escaped}",i];'
        f"out center tags {_MAX_SEARCH_RESULTS};"
    )
    data = await _run_query(ql)

    summaries = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        center = el.get("center")
        summaries.append(
            OsmCourseSummary(
                osm_type=el["type"],
                osm_id=el["id"],
                name=name,
                city=tags.get("addr:city"),
                state=tags.get("addr:state"),
                center=LatLng(lat=center["lat"], lng=center["lon"]) if center else None,
            )
        )
    return summaries


async def fetch_course_geometry(osm_type: str, osm_id: int) -> OsmCourseDetail:
    """Fetches hole/tee/green geometry within a course's OSM area and
    resolves each hole's tee/green by nearest-endpoint matching."""
    ql = (
        "[out:json][timeout:25];"
        f"{osm_type}({osm_id});"
        "map_to_area->.course;"
        "("
        'way["golf"="hole"](area.course);'
        'way["golf"="tee"](area.course);'
        'node["golf"="tee"](area.course);'
        'way["golf"="green"](area.course);'
        ");"
        "out geom tags;"
    )
    course_ql = f"[out:json][timeout:25];{osm_type}({osm_id});out tags;"

    data = await _run_query(ql)
    course_data = await _run_query(course_ql)
    course_tags = _first_tags(course_data)

    holes_raw, tees, greens = [], [], []
    for el in data.get("elements", []):
        golf = el.get("tags", {}).get("golf")
        if golf == "hole":
            holes_raw.append(el)
        elif golf == "tee":
            tees.append(el)
        elif golf == "green":
            greens.append(el)

    holes = [_build_hole_candidate(hole_el, tees, greens) for hole_el in holes_raw]
    holes.sort(key=lambda h: (h.number is None, h.number or 0))

    return OsmCourseDetail(
        osm_id=osm_id,
        name=course_tags.get("name", ""),
        city=course_tags.get("addr:city"),
        state=course_tags.get("addr:state"),
        holes=holes,
    )


def _first_tags(data: dict) -> dict:
    elements = data.get("elements", [])
    return elements[0].get("tags", {}) if elements else {}


def _element_geometry(el: dict) -> list[LatLng]:
    if "geometry" in el:  # way, from `out geom`
        return [LatLng(lat=pt["lat"], lng=pt["lon"]) for pt in el["geometry"]]
    if "lat" in el:  # node
        return [LatLng(lat=el["lat"], lng=el["lon"])]
    return []


def _centroid(points: list[LatLng]) -> LatLng | None:
    if not points:
        return None
    return LatLng(
        lat=sum(p.lat for p in points) / len(points),
        lng=sum(p.lng for p in points) / len(points),
    )


def _distance_yards(a: LatLng, b: LatLng) -> float:
    east, north = local_yards(a, b)
    return math.hypot(east, north)


def _nearest_feature_geometry(
    anchor: LatLng, features: list[dict], max_distance_yards: float
) -> list[LatLng] | None:
    best: tuple[float, list[LatLng]] | None = None
    for el in features:
        points = _element_geometry(el)
        centroid = _centroid(points)
        if centroid is None:
            continue
        distance = _distance_yards(anchor, centroid)
        if distance <= max_distance_yards and (best is None or distance < best[0]):
            best = (distance, points)
    return best[1] if best else None


def _parse_int_tag(tags: dict, key: str) -> int | None:
    value = tags.get(key)
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _build_hole_candidate(
    hole_el: dict, tees: list[dict], greens: list[dict]
) -> OsmHoleCandidate:
    tags = hole_el.get("tags", {})
    geometry = _element_geometry(hole_el)
    number = _parse_int_tag(tags, "ref")
    par = _parse_int_tag(tags, "par")

    if not geometry:
        return OsmHoleCandidate(
            number=number, par=par, yardage=None,
            tee_location=None, green_center=None, green_boundary=None,
        )

    tee_anchor, green_anchor = geometry[0], geometry[-1]

    tee_points = _nearest_feature_geometry(tee_anchor, tees, _MAX_MATCH_DISTANCE_YARDS)
    tee_location = _centroid(tee_points) if tee_points else tee_anchor

    green_points = _nearest_feature_geometry(green_anchor, greens, _MAX_MATCH_DISTANCE_YARDS)
    green_center = _centroid(green_points) if green_points else green_anchor
    green_boundary = green_points if green_points and len(green_points) >= 3 else None

    yardage = round(
        sum(_distance_yards(geometry[i], geometry[i + 1]) for i in range(len(geometry) - 1))
    )

    return OsmHoleCandidate(
        number=number, par=par, yardage=yardage,
        tee_location=tee_location, green_center=green_center, green_boundary=green_boundary,
    )
