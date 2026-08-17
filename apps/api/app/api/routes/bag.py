from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.routes._shot_queries import club_gapping_with_lateral
from app.services.dispersion import compute_dispersion_ellipse
from app.services.smart_bag import compute_gaps

router = APIRouter()


@router.get("/bag")
def get_smart_bag(user: CurrentUser, session: SessionDep) -> dict:
    """Smart Bag club gapping (PRD §5.3): outlier-filtered carry stats per
    club, aggregated across every round this user has played, plus the
    consecutive-club carry gaps in bag order. Lateral dispersion and a
    dispersion ellipse are included for clubs with at least one
    location-tagged shot (PRD §10 Phase 4 — see app/services/geometry.py for
    where the lateral offset comes from).
    """
    # Carry dispersion is computed in SQL (Phase 16 — see
    # _shot_queries.py's club_carry_dispersion_sql), so this no longer
    # walks every shot the player has ever recorded into Python.
    stats = club_gapping_with_lateral(session, user.id)
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
        "user_id": user.id,
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
