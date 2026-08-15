from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import Hole, Round, Shot, User
from app.services.approach import classify_approach_leave
from app.services.putting import evaluate_putting
from app.services.strokes_gained import compute_round_strokes_gained
from app.services.tiger_five import evaluate_round

router = APIRouter()


@router.get("/rounds")
def list_rounds(session: Annotated[Session, Depends(get_session)]) -> list[Round]:
    return list(session.exec(select(Round)).all())


@router.get("/rounds/{round_id}/shots")
def list_round_shots(
    round_id: int, session: Annotated[Session, Depends(get_session)]
) -> list[Shot]:
    round_ = session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return list(
        session.exec(select(Shot).where(Shot.round_id == round_id).order_by(Shot.id)).all()
    )


@router.get("/rounds/{round_id}/analytics")
def get_round_analytics(
    round_id: int, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Round-level diagnostics (PRD §5, §8): Strokes Gained by category,
    Tiger 5 violations + Clean Card Index, putting mechanics, and a
    per-shot breakdown. Also persists the computed `Shot.strokes_gained`
    back onto each shot.
    """
    round_ = session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")

    user = session.get(User, round_.user_id)
    handicap_index = user.handicap_index if user else 0.0

    shots = list(
        session.exec(select(Shot).where(Shot.round_id == round_id).order_by(Shot.id)).all()
    )
    holes = {
        hole.id: hole
        for hole in session.exec(select(Hole).where(Hole.course_id == round_.course_id)).all()
    }

    sg_summary = compute_round_strokes_gained(
        [(shot, holes[shot.hole_id].par) for shot in shots], handicap_index
    )

    sg_by_shot_id = {r.shot_id: r for r in sg_summary.shots}
    for shot in shots:
        result = sg_by_shot_id.get(shot.id)
        shot.strokes_gained = result.strokes_gained if result else None
        session.add(shot)
    session.commit()

    shots_by_hole: dict[int, list[Shot]] = defaultdict(list)
    for shot in shots:
        shots_by_hole[shot.hole_id].append(shot)
    tiger_five = evaluate_round(
        [
            (holes[hole_id].number, holes[hole_id].par, hole_shots)
            for hole_id, hole_shots in shots_by_hole.items()
        ]
    )
    putting = evaluate_putting(shots)

    return {
        "round_id": round_id,
        "handicap_bucket": sg_summary.handicap_bucket,
        "strokes_gained": {
            "total": round(sg_summary.total, 2),
            "by_category": {c.value: round(v, 2) for c, v in sg_summary.by_category.items()},
        },
        "tiger_five": {
            "double_bogeys_or_worse": tiger_five.double_bogeys_or_worse,
            "three_putts": tiger_five.three_putts,
            "par_five_bogeys": tiger_five.par_five_bogeys,
            "blown_recoveries_inside_50": tiger_five.blown_recoveries_inside_50,
            "penalties_inside_150": tiger_five.penalties_inside_150,
            "clean_card_index": tiger_five.clean_card_index,
        },
        "putting": {
            "lag_putt_count": putting.lag_putt_count,
            "lag_efficiency_pct": putting.lag_efficiency_pct,
            "average_lag_proximity_yards": putting.average_lag_proximity_yards,
            "short_putt_count": putting.short_putt_count,
            "start_line_conversion_pct": putting.start_line_conversion_pct,
        },
        "shots": [
            {
                "shot_id": r.shot_id,
                "category": r.category.value,
                "strokes_gained": round(r.strokes_gained, 3),
                "approach_leave": classify_approach_leave(shot).value,
            }
            for r, shot in zip(sg_summary.shots, shots, strict=True)
        ],
    }
