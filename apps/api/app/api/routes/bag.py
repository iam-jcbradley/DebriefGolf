from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import Hole, Round, Shot
from app.services.dispersion import compute_dispersion_ellipse
from app.services.geometry import ShotGeometryRow, compute_lateral_by_club
from app.services.smart_bag import compute_club_gapping, compute_gaps, shot_carry_distance

router = APIRouter()


def _fetch_shot_geometry_rows(session: Session, round_ids: list[int]) -> list[ShotGeometryRow]:
    if not round_ids:
        return []

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
        .where(Shot.round_id.in_(round_ids))
        .where(Shot.club.is_not(None))
        .where(Shot.location.is_not(None))
        .where(Hole.tee_location.is_not(None))
        .where(Hole.green_center.is_not(None))
    )
    return [ShotGeometryRow(**row._mapping) for row in session.exec(query)]  # type: ignore[arg-type]


@router.get("/bag/{user_id}")
def get_smart_bag(user_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Smart Bag club gapping (PRD §5.3): outlier-filtered carry stats per
    club, aggregated across every round this user has played, plus the
    consecutive-club carry gaps in bag order. Lateral dispersion and a
    dispersion ellipse are included for clubs with at least one
    location-tagged shot (PRD §10 Phase 4 — see app/services/geometry.py for
    where the lateral offset comes from).
    """
    round_ids = list(
        session.exec(select(Round.id).where(Round.user_id == user_id)).all()
    )
    shots: list[Shot] = []
    if round_ids:
        shots = list(session.exec(select(Shot).where(Shot.round_id.in_(round_ids))).all())

    distances_by_club: dict[str, list[float]] = defaultdict(list)
    for shot in shots:
        distance = shot_carry_distance(shot)
        if distance is not None and distance > 0 and shot.club is not None:
            distances_by_club[shot.club].append(distance)

    lateral_by_club = compute_lateral_by_club(_fetch_shot_geometry_rows(session, round_ids))

    stats = compute_club_gapping(distances_by_club, lateral_by_club=lateral_by_club)
    gaps = compute_gaps(stats)

    clubs = []
    for s in stats:
        club_payload = {
            "club": s.club,
            "sample_count": s.carry.count,
            "excluded_outliers": s.carry.excluded_outliers,
            "carry_mean_yards": round(s.carry.mean, 1),
            "carry_median_yards": round(s.carry.median, 1),
            "carry_stdev_yards": round(s.carry.stdev, 1),
            "lateral_mean_yards": None,
            "lateral_stdev_yards": None,
            "dispersion_ellipse": None,
        }
        if s.lateral is not None and s.lateral.count > 0:
            club_payload["lateral_mean_yards"] = round(s.lateral.mean, 1)
            club_payload["lateral_stdev_yards"] = round(s.lateral.stdev, 1)
            ellipse = compute_dispersion_ellipse(
                longitudinal_mean_yards=s.carry.mean,
                longitudinal_stdev_yards=s.carry.stdev,
                lateral_mean_yards=s.lateral.mean,
                lateral_stdev_yards=s.lateral.stdev,
            )
            club_payload["dispersion_ellipse"] = {
                "center_longitudinal_yards": round(ellipse.center_longitudinal_yards, 1),
                "center_lateral_yards": round(ellipse.center_lateral_yards, 1),
                "semi_major_yards": round(ellipse.semi_major_yards, 1),
                "semi_minor_yards": round(ellipse.semi_minor_yards, 1),
                "k": ellipse.k,
            }
        clubs.append(club_payload)

    return {
        "user_id": user_id,
        "clubs": clubs,
        "gaps": [
            {
                "longer_club": g.longer_club,
                "shorter_club": g.shorter_club,
                "carry_gap_yards": g.carry_gap_yards,
            }
            for g in gaps
        ],
    }
