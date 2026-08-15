from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import Round, Shot
from app.services.smart_bag import compute_club_gapping, compute_gaps, shot_carry_distance

router = APIRouter()


@router.get("/bag/{user_id}")
def get_smart_bag(user_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Smart Bag club gapping (PRD §5.3): outlier-filtered carry stats per
    club, aggregated across every round this user has played, plus the
    consecutive-club carry gaps in bag order.
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

    stats = compute_club_gapping(distances_by_club)
    gaps = compute_gaps(stats)

    return {
        "user_id": user_id,
        "clubs": [
            {
                "club": s.club,
                "sample_count": s.carry.count,
                "excluded_outliers": s.carry.excluded_outliers,
                "carry_mean_yards": round(s.carry.mean, 1),
                "carry_median_yards": round(s.carry.median, 1),
                "carry_stdev_yards": round(s.carry.stdev, 1),
            }
            for s in stats
        ],
        "gaps": [
            {
                "longer_club": g.longer_club,
                "shorter_club": g.shorter_club,
                "carry_gap_yards": g.carry_gap_yards,
            }
            for g in gaps
        ],
    }
