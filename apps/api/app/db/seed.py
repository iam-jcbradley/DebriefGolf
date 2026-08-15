"""Populate the database with reference and demo data for local development/testing.

`seed_benchmarks()` populates the Strokes Gained benchmark lookup table
(reference data the Phase 2 SG engine benchmarks against).

`seed()` produces a single Course (18 holes), a demo User, and a Round scored
78 (+6 on a par-72) with shot-by-shot detail — including a handful of
scenarios the PRD's diagnostics are meant to catch: a short-sided bunker
approach (PRD §8's example), a 3-putt, a penalty stroke inside 150y, and a
par-5 bogey — so downstream analytics (Phase 2+) has something realistic to
chew on.

Usage: uv run python -m app.db.seed
"""

import math
import random

from geoalchemy2.elements import WKTElement
from sqlmodel import Session, select

from app.db.session import engine
from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, StrokesGainedBenchmark, User
from app.services.benchmarks import generate_benchmark_rows

DEMO_EMAIL = "demo@debriefgolf.app"
COURSE_NAME = "Pinehurst Creek Golf Club"

# (par, yardage)
HOLE_LAYOUT = [
    (4, 400), (4, 385), (3, 175), (5, 540), (4, 410), (3, 160), (4, 418),
    (5, 525), (4, 395), (4, 405), (3, 190), (5, 555), (4, 375), (4, 410),
    (3, 170), (4, 440), (5, 510), (4, 430),
]

# Base coordinates are arbitrary (coastal South Carolina-ish) — this is a
# fictional course, geometry only needs to be valid, not surveyed.
BASE_LAT, BASE_LNG = 33.7000, -78.9000
YARDS_PER_DEGREE_LAT = 121000.0


def _move(lat: float, lng: float, bearing_deg: float, yards: float) -> tuple[float, float]:
    d_lat = (yards * math.cos(math.radians(bearing_deg))) / YARDS_PER_DEGREE_LAT
    d_lng = (yards * math.sin(math.radians(bearing_deg))) / (
        YARDS_PER_DEGREE_LAT * math.cos(math.radians(lat))
    )
    return lat + d_lat, lng + d_lng


def _point(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def _green_boundary(lat: float, lng: float, radius_yards: float = 15) -> WKTElement:
    pts = []
    for i in range(9):
        bearing = i * (360 / 8)
        plat, plng = _move(lat, lng, bearing, radius_yards)
        pts.append(f"{plng} {plat}")
    return WKTElement(f"POLYGON(({', '.join(pts)}))", srid=4326)


# Fixed seed: demo data must stay reproducible across reseeds.
_LATERAL_RNG = random.Random(42)


def _lateral_offset_yards(shot: dict) -> float:
    """A rough, deterministic lateral miss (yards right of the tee->green
    aim line; negative = left) for plotting on the hole replay map and for
    Smart Bag lateral dispersion (PRD §5.3) — there's no real swing physics
    here, just enough variance for the demo data to look like real shots
    and for the narrative tags (§ SPECIAL_HOLES) to visually match their
    story."""
    club = shot.get("club")
    if club is None or club == "Putter":
        return 0.0  # no lateral "miss" concept for a penalty marker or a putt
    tag = shot.get("tag") or ""
    if "OB" in tag:
        return _LATERAL_RNG.uniform(18, 28)
    if "Push" in tag or "Slice" in tag:
        return _LATERAL_RNG.uniform(10, 16)
    if "Short-Sided" in tag:
        return _LATERAL_RNG.uniform(6, 10)
    return _LATERAL_RNG.uniform(-6, 6)


def _shot_location(
    tee_lat: float, tee_lng: float, bearing: float, yardage: float,
    start_distance: float, end_distance: float, lateral_yards: float,
) -> WKTElement | None:
    """The shot's landing point, projected along the hole's tee->green aim
    line at (yardage - end_distance) from the tee, offset sideways by
    `lateral_yards`.

    Returns `None` when the shot recorded no forward progress
    (`end_distance >= start_distance`) — a penalty-stroke marker or a
    stroke-and-distance reset (PRD §4.2). Those don't have a real physical
    position in this data model (the SG formula only cares that the
    distance-to-hole didn't improve, not where the lost/OB ball actually
    went), so this deliberately leaves `location` unset rather than
    fabricating a plausible-looking coordinate nothing backs.
    """
    if end_distance >= start_distance:
        return None
    distance_from_tee = max(yardage - end_distance, 0.0)
    lat, lng = _move(tee_lat, tee_lng, bearing, distance_from_tee)
    if lateral_yards:
        lat, lng = _move(lat, lng, bearing + 90, lateral_yards)
    return _point(lat, lng)


def approach_club_for(yards: float) -> str:
    brackets = [
        (200, "4-Iron"), (175, "5-Iron"), (160, "6-Iron"), (140, "7-Iron"),
        (120, "8-Iron"), (100, "9-Iron"), (80, "PW"),
    ]
    for threshold, club in brackets:
        if yards > threshold:
            return club
    return "SW"


ON_GREEN_LAG = 6.7  # ~20ft, in yards
ON_GREEN_SHORT = 1.3  # ~4ft
TAP_IN = 0.3  # ~1ft


def _par_shots(
    par: int, yardage: float, extra_putt: bool = False, one_putt: bool = False
) -> list[dict]:
    """Generic 'played it straight' hole: GIR (or 1-under-GIR for par 5s) plus putts."""
    shots: list[dict] = []
    if par == 3:
        shots.append(
            dict(club=approach_club_for(yardage), start_lie=Lie.tee, end_lie=Lie.green,
                 start=yardage, end=ON_GREEN_LAG)
        )
    else:
        approach_start = yardage * 0.4
        shots.append(dict(club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway,
                           start=yardage, end=approach_start))
        if par == 5:
            layup_end = approach_start * 0.35
            shots.append(dict(club="3-Wood", start_lie=Lie.fairway, end_lie=Lie.fairway,
                               start=approach_start, end=layup_end))
            approach_start = layup_end
        shots.append(dict(club=approach_club_for(approach_start), start_lie=Lie.fairway,
                           end_lie=Lie.green, start=approach_start, end=ON_GREEN_LAG))

    if one_putt:
        shots.append(dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole,
                           start=ON_GREEN_LAG, end=0))
    else:
        shots.append(dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green,
                           start=ON_GREEN_LAG, end=ON_GREEN_SHORT))
        shots.append(dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole,
                           start=ON_GREEN_SHORT, end=0))
        if extra_putt:
            shots.insert(-1, dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green,
                                   start=ON_GREEN_SHORT, end=TAP_IN, tag="Lag Putt"))
    return shots


# Hand-scripted narrative holes. Keys are 1-indexed hole numbers.
SPECIAL_HOLES: dict[int, list[dict]] = {
    2: [  # double bogey via OB tee shot (PRD §4.2 penalty drop wizard territory)
        dict(club="Driver", start_lie=Lie.tee, end_lie=Lie.penalty, start=385, end=385,
             tag="OB Right"),
        dict(club=None, start_lie=Lie.penalty, end_lie=Lie.penalty, start=385, end=385,
             tag="Penalty: Stroke & Distance"),
        dict(club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway, start=385, end=150),
        dict(club="8-Iron", start_lie=Lie.fairway, end_lie=Lie.green, start=150, end=ON_GREEN_LAG),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green,
             start=ON_GREEN_LAG, end=ON_GREEN_SHORT),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole, start=ON_GREEN_SHORT, end=0),
    ],
    7: [  # PRD §8 UI mockup example, verbatim: heel/push-slice into a short-sided bunker
        dict(club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway, start=418, end=162),
        dict(club="7-Iron", start_lie=Lie.fairway, end_lie=Lie.sand, start=162, end=12,
             tag="Heel / Push-Slice"),
        dict(club="SW", start_lie=Lie.sand, end_lie=Lie.green, start=12, end=3.3),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green, start=3.3, end=ON_GREEN_SHORT),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole, start=ON_GREEN_SHORT, end=0),
    ],
    9: [  # 3-putt bogey (lag speed / start-line diagnostics, PRD §5.2)
        dict(club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway, start=395, end=165),
        dict(club="6-Iron", start_lie=Lie.fairway, end_lie=Lie.green, start=165, end=ON_GREEN_LAG),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green, start=ON_GREEN_LAG, end=2.0,
             tag="Lag Putt"),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green, start=2.0, end=TAP_IN),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole, start=TAP_IN, end=0),
    ],
    14: [  # penalty inside 150y (PRD §5.2 Tiger 5) with a bogey save
        dict(club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway, start=410, end=140),
        dict(club="8-Iron", start_lie=Lie.fairway, end_lie=Lie.penalty, start=140, end=140,
             tag="Approach: Water Hazard"),
        dict(club=None, start_lie=Lie.penalty, end_lie=Lie.penalty, start=140, end=140,
             tag="Penalty: Lateral Hazard Drop"),
        dict(club="SW", start_lie=Lie.penalty, end_lie=Lie.green, start=130, end=1.7),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole, start=1.7, end=0),
    ],
    17: [  # Par 5 bogey via a missed/short-sided green (PRD §5.2 Tiger 5)
        dict(club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway, start=510, end=210),
        dict(club="3-Wood", start_lie=Lie.fairway, end_lie=Lie.fairway, start=210, end=90),
        dict(club="PW", start_lie=Lie.fairway, end_lie=Lie.rough, start=90, end=8,
             tag="Missed Green / Short-Sided"),
        dict(club="SW", start_lie=Lie.rough, end_lie=Lie.green, start=8, end=4.3),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green, start=4.3, end=ON_GREEN_SHORT),
        dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole, start=ON_GREEN_SHORT, end=0),
    ],
}


def build_hole_shots(number: int, par: int, yardage: float) -> list[dict]:
    if number in SPECIAL_HOLES:
        return SPECIAL_HOLES[number]
    if number == 6:  # bogey via greenside bunker
        return [
            dict(club=approach_club_for(yardage), start_lie=Lie.tee, end_lie=Lie.sand,
                 start=yardage, end=8),
            dict(club="SW", start_lie=Lie.sand, end_lie=Lie.green, start=8, end=3.3),
            dict(club="Putter", start_lie=Lie.green, end_lie=Lie.green,
                 start=3.3, end=ON_GREEN_SHORT),
            dict(club="Putter", start_lie=Lie.green, end_lie=Lie.hole, start=ON_GREEN_SHORT, end=0),
        ]
    if number == 4:  # birdie
        return _par_shots(par, yardage, one_putt=True)
    return _par_shots(par, yardage)


def seed_benchmarks() -> None:
    """Populate the Strokes Gained benchmark lookup table (PRD §5.1, §10 Phase 1).

    Independent of `seed()` below — this is reference data the SG engine
    benchmarks against, not sample round data.
    """
    with Session(engine) as session:
        existing = session.exec(select(StrokesGainedBenchmark).limit(1)).first()
        if existing:
            print("strokes_gained_benchmark already populated; skipping.")
            return

        rows = generate_benchmark_rows()
        session.add_all(StrokesGainedBenchmark(**row) for row in rows)
        session.commit()
        print(f"Seeded {len(rows)} Strokes Gained benchmark rows.")


def seed() -> None:
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == DEMO_EMAIL)).first()
        if existing:
            print(f"Demo user {DEMO_EMAIL} already exists (id={existing.id}); skipping seed.")
            print("Delete the row (or the db_data volume) and re-run to reseed.")
            return

        user = User(email=DEMO_EMAIL, name="Demo Golfer", handicap_index=5.0)
        course = Course(name=COURSE_NAME, city="Pawleys Island", state="SC")
        session.add(user)
        session.add(course)
        session.commit()
        session.refresh(user)
        session.refresh(course)

        lat, lng = BASE_LAT, BASE_LNG
        bearing = 0.0
        holes: list[Hole] = []
        # tee lat/lng + tee->green bearing per hole, kept for shot-location
        # projection below (Hole.tee_location is WKT once persisted, not
        # convenient to re-parse).
        hole_geo: dict[int, tuple[float, float, float]] = {}
        for number, (par, yardage) in enumerate(HOLE_LAYOUT, start=1):
            tee_lat, tee_lng = lat, lng
            green_lat, green_lng = _move(tee_lat, tee_lng, bearing, yardage)
            hole = Hole(
                course_id=course.id,
                number=number,
                par=par,
                yardage=yardage,
                tee_location=_point(tee_lat, tee_lng),
                green_center=_point(green_lat, green_lng),
                green_boundary=_green_boundary(green_lat, green_lng),
            )
            session.add(hole)
            holes.append(hole)
            hole_geo[number] = (tee_lat, tee_lng, bearing)
            bearing = (bearing + 35) % 360
            lat, lng = _move(green_lat, green_lng, bearing, 40)
        session.commit()
        for hole in holes:
            session.refresh(hole)

        total_score = sum(len(build_hole_shots(h.number, h.par, h.yardage)) for h in holes)
        round_ = Round(
            user_id=user.id,
            course_id=course.id,
            total_score=total_score,
            status=RoundStatus.verified,
        )
        session.add(round_)
        session.commit()
        session.refresh(round_)

        shot_count = 0
        for hole in holes:
            tee_lat, tee_lng, bearing = hole_geo[hole.number]
            for shot_number, s in enumerate(
                build_hole_shots(hole.number, hole.par, hole.yardage), start=1
            ):
                location = _shot_location(
                    tee_lat, tee_lng, bearing, hole.yardage,
                    s["start"], s["end"], _lateral_offset_yards(s),
                )
                session.add(
                    Shot(
                        round_id=round_.id,
                        hole_id=hole.id,
                        shot_number=shot_number,
                        club=s["club"],
                        start_lie=s["start_lie"],
                        end_lie=s["end_lie"],
                        start_distance_yards=s["start"],
                        end_distance_yards=s["end"],
                        location=location,
                        tag=s.get("tag"),
                    )
                )
                shot_count += 1
        session.commit()

        par_total = sum(par for par, _ in HOLE_LAYOUT)
        print(
            f"Seeded {course.name}: {len(holes)} holes (par {par_total}), "
            f"1 round for {user.email} — score {total_score} "
            f"({total_score - par_total:+d}), {shot_count} shots."
        )


if __name__ == "__main__":
    seed_benchmarks()
    seed()
