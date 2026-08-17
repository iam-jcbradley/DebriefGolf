"""Shared on-course-shot query helpers for `GET /bag` and `GET /practice/*`
(Phase 6, Phase 4's lateral dispersion). Lives in `app/api/routes/`, not
`app/services/`, since these touch the database session directly — see
CLAUDE.md's layering note on why persistence stays out of `services/`.

`club_gapping_with_lateral` exists to fix a real bug (found by the QA panel
gut-check, see docs/KNOWN_ISSUES.md): `practice.py`'s driver-dispersion
combine detector used to call `compute_club_gapping` without
`lateral_by_club`, so `ClubGappingStats.lateral` was always `None` and the
combine could never fire, while `bag.py`'s independent copy of the same
computation got it right. One function now, called from both, so a future
fix to this logic can't drift between the two call sites again.
"""

from collections import defaultdict

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Hole, Round, Shot
from app.services.geometry import ShotGeometryRow, compute_lateral_by_club
from app.services.shot_view import ShotView
from app.services.smart_bag import ClubGappingStats, compute_club_gapping, shot_carry_distance


def fetch_on_course_shots(session: Session, user_id: int) -> list[ShotView]:
    """Every on-course shot this user has recorded, as raw columns rather
    than ORM objects — see app/services/shot_view.py for why."""
    return list(
        session.exec(
            select(
                Shot.club,
                Shot.start_distance_yards,
                Shot.end_distance_yards,
                Shot.end_lie,
                Shot.strokes_gained,
            )
            .join(Round, Shot.round_id == Round.id)
            .where(Round.user_id == user_id)
        ).all()
    )


def fetch_shot_geometry_rows(session: Session, user_id: int) -> list[ShotGeometryRow]:
    """Every located on-course shot plus its hole's tee/green — the input
    `compute_lateral_by_club` needs to turn a GPS point into a lateral
    aim-line offset."""
    query = (
        select(
            Shot.club,
            func.ST_Y(Shot.location).label("shot_lat"),
            func.ST_X(Shot.location).label("shot_lng"),
            func.ST_Y(Hole.tee_location).label("tee_lat"),
            func.ST_X(Hole.tee_location).label("tee_lng"),
            func.ST_Y(Hole.green_center).label("green_lat"),
            func.ST_X(Hole.green_center).label("green_lng"),
        )
        .join(Hole, Shot.hole_id == Hole.id)
        .join(Round, Shot.round_id == Round.id)
        .where(Round.user_id == user_id)
        .where(Shot.club.is_not(None))
        .where(Shot.location.is_not(None))
        .where(Hole.tee_location.is_not(None))
        .where(Hole.green_center.is_not(None))
    )
    return [ShotGeometryRow(**row._mapping) for row in session.exec(query)]  # type: ignore[arg-type]


def club_gapping_with_lateral(
    session: Session, user_id: int, on_course_shots: list[ShotView]
) -> list[ClubGappingStats]:
    """Carry *and* lateral dispersion per club. `on_course_shots` is passed
    in rather than re-queried, since every current caller already has it
    from `fetch_on_course_shots` for another purpose — this only adds the
    one extra geometry-joined query lateral dispersion actually needs."""
    distances_by_club: dict[str, list[float]] = defaultdict(list)
    for shot in on_course_shots:
        distance = shot_carry_distance(shot)
        if distance is not None and distance > 0 and shot.club is not None:
            distances_by_club[shot.club].append(distance)

    lateral_by_club = compute_lateral_by_club(fetch_shot_geometry_rows(session, user_id))
    return compute_club_gapping(distances_by_club, lateral_by_club=lateral_by_club)
