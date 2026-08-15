"""Practice Hub endpoints (PRD §6.1, §7.1, §10 Phase 6): R10/R50 session
ingestion, the aggregated delivery profile + Sim vs. Real-World gapping
delta, and prescriptive practice combine recommendations.
"""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import PracticeSession, PracticeShot, Round, Shot, User
from app.services.delivery_profile import (
    SessionShotRow,
    compute_delivery_profile,
    compute_delivery_trend,
    compute_gapping_delta,
)
from app.services.parsers.launch_monitor_parser import (
    parse_launch_monitor_csv,
    parse_launch_monitor_json,
)
from app.services.practice_combines import (
    APPROACH_WEAKNESS_MAX_YARDS,
    APPROACH_WEAKNESS_MIN_YARDS,
    detect_approach_weakness,
    detect_driver_dispersion_weakness,
    detect_iron_strike_weakness,
    detect_putting_lag_weakness,
    recommend_combines,
)
from app.services.putting import evaluate_putting
from app.services.smart_bag import CLUB_ORDER, compute_club_gapping, shot_carry_distance

router = APIRouter()

IRON_CLUBS = {club for club in CLUB_ORDER if "Iron" in club}


@router.post("/practice/sessions/upload", status_code=201)
async def upload_practice_session(
    user_id: int,
    source: str,
    file: UploadFile,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Ingest an R10/R50 export: parses it with
    `app.services.parsers.launch_monitor_parser` (CSV, or JSON when the
    filename ends `.json`) and persists every successfully-parsed shot as a
    `PracticeShot` under a new `PracticeSession`. `source` is freeform
    (e.g. "R10", "R50") — no fixed device enum, matching the parser's own
    header-alias tolerance. Malformed rows don't abort the upload; they're
    reported back alongside the created session.
    """
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    contents = await file.read()
    is_json = (file.filename or "").lower().endswith(".json")
    result = (
        parse_launch_monitor_json(contents) if is_json else parse_launch_monitor_csv(contents)
    )

    if not result.shots:
        raise HTTPException(
            status_code=422,
            detail=f"No shots could be parsed from this file. Errors: {result.errors}",
        )

    practice_session = PracticeSession(user_id=user_id, source=source)
    session.add(practice_session)
    session.commit()
    session.refresh(practice_session)

    for shot in result.shots:
        session.add(
            PracticeShot(
                session_id=practice_session.id,
                club=shot.club,
                club_speed_mph=shot.club_speed_mph,
                ball_speed_mph=shot.ball_speed_mph,
                smash_factor=shot.smash_factor,
                launch_angle_deg=shot.launch_angle_deg,
                spin_rate_rpm=shot.spin_rate_rpm,
                spin_axis_deg=shot.spin_axis_deg,
                club_path_deg=shot.club_path_deg,
                face_angle_deg=shot.face_angle_deg,
                carry_yards=shot.carry_yards,
                total_yards=shot.total_yards,
                captured_at=shot.captured_at,
            )
        )
    session.commit()

    return {
        "session_id": practice_session.id,
        "shot_count": len(result.shots),
        "errors": result.errors,
    }


def _fetch_on_course_shots(session: Session, user_id: int) -> list[Shot]:
    round_ids = list(session.exec(select(Round.id).where(Round.user_id == user_id)).all())
    if not round_ids:
        return []
    return list(session.exec(select(Shot).where(Shot.round_id.in_(round_ids))).all())


def _on_course_club_gapping(shots: list[Shot]) -> list:
    distances_by_club: dict[str, list[float]] = defaultdict(list)
    for shot in shots:
        distance = shot_carry_distance(shot)
        if distance is not None and distance > 0 and shot.club is not None:
            distances_by_club[shot.club].append(distance)
    return compute_club_gapping(distances_by_club)


@router.get("/practice/delivery/{user_id}")
def get_delivery_profile(user_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Per-club R10/R50 delivery numbers (PRD §6.1): aggregate averages,
    a per-club trend across sessions, and the Sim vs. Real-World carry
    gapping delta against this user's on-course Smart Bag numbers.
    """
    practice_sessions = list(
        session.exec(select(PracticeSession).where(PracticeSession.user_id == user_id)).all()
    )
    recorded_at_by_session = {s.id: s.recorded_at for s in practice_sessions}
    session_ids = list(recorded_at_by_session.keys())

    practice_shots: list[PracticeShot] = []
    if session_ids:
        practice_shots = list(
            session.exec(select(PracticeShot).where(PracticeShot.session_id.in_(session_ids))).all()
        )

    profile = compute_delivery_profile(practice_shots)
    trend = compute_delivery_trend(
        [
            SessionShotRow(
                session_id=s.session_id,
                recorded_at=recorded_at_by_session[s.session_id],
                shot=s,
            )
            for s in practice_shots
        ]
    )

    on_course_stats = _on_course_club_gapping(_fetch_on_course_shots(session, user_id))
    gapping = compute_gapping_delta(profile, on_course_stats)

    return {
        "user_id": user_id,
        "session_count": len(practice_sessions),
        "clubs": [
            {
                "club": p.club,
                "shot_count": p.shot_count,
                "avg_club_path_deg": p.avg_club_path_deg,
                "avg_face_angle_deg": p.avg_face_angle_deg,
                "avg_face_to_path_deg": p.avg_face_to_path_deg,
                "avg_spin_axis_deg": p.avg_spin_axis_deg,
                "avg_smash_factor": p.avg_smash_factor,
                "avg_carry_yards": p.avg_carry_yards,
            }
            for p in profile
        ],
        "trend": {
            club: [
                {
                    "session_id": pt.session_id,
                    "recorded_at": pt.recorded_at.isoformat(),
                    "shot_count": pt.shot_count,
                    "avg_carry_yards": pt.avg_carry_yards,
                    "avg_smash_factor": pt.avg_smash_factor,
                    "avg_face_to_path_deg": pt.avg_face_to_path_deg,
                    "avg_spin_axis_deg": pt.avg_spin_axis_deg,
                }
                for pt in points
            ]
            for club, points in trend.items()
        },
        "sim_vs_real_gapping": [
            {
                "club": g.club,
                "range_carry_mean_yards": g.range_carry_mean_yards,
                "on_course_carry_mean_yards": g.on_course_carry_mean_yards,
                "delta_yards": g.delta_yards,
            }
            for g in gapping
        ],
    }


@router.get("/practice/combines/{user_id}")
def get_practice_combines(user_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Prescriptive combine recommendations (PRD §7.1): detects the four
    PRD §7.1 weaknesses from data this user already has on file — on-course
    Strokes Gained from 100-125y, Smart Bag driver dispersion, R10/R50 iron
    smash factor, and putting lag efficiency — and returns a combine per
    weakness actually detected. A user with no weaknesses flagged (or no
    data at all yet) gets an empty list, not a default recommendation.
    """
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    on_course_shots = _fetch_on_course_shots(session, user_id)

    approach_bracket_sg = [
        shot.strokes_gained
        for shot in on_course_shots
        if shot.strokes_gained is not None
        and shot.club != "Putter"
        and APPROACH_WEAKNESS_MIN_YARDS <= shot.start_distance_yards <= APPROACH_WEAKNESS_MAX_YARDS
    ]

    driver_stats = next(
        (s for s in _on_course_club_gapping(on_course_shots) if s.club == "Driver"), None
    )
    driver_lateral_stdev = (
        driver_stats.lateral.stdev if driver_stats and driver_stats.lateral else None
    )

    practice_session_ids = list(
        session.exec(select(PracticeSession.id).where(PracticeSession.user_id == user_id)).all()
    )
    smash_factor_by_iron: dict[str, list[float]] = defaultdict(list)
    if practice_session_ids:
        iron_shots = list(
            session.exec(
                select(PracticeShot).where(
                    PracticeShot.session_id.in_(practice_session_ids),
                    PracticeShot.club.in_(IRON_CLUBS),
                )
            ).all()
        )
        for shot in iron_shots:
            if shot.smash_factor is not None:
                smash_factor_by_iron[shot.club].append(shot.smash_factor)

    putting = evaluate_putting(on_course_shots)

    signals = [
        detect_approach_weakness(approach_bracket_sg),
        detect_driver_dispersion_weakness(driver_lateral_stdev),
        detect_iron_strike_weakness(smash_factor_by_iron),
        detect_putting_lag_weakness(putting.lag_efficiency_pct, putting.lag_putt_count),
    ]
    signals = [s for s in signals if s is not None]
    combines = recommend_combines(signals)

    return {
        "user_id": user_id,
        "weaknesses": [
            {"weakness": s.weakness.value, "detail": s.detail} for s in signals
        ],
        "combines": [
            {
                "weakness": c.weakness.value,
                "name": c.name,
                "instructions": c.instructions,
                "target_metric": c.target_metric,
                "video_search_url": c.video_search_url,
            }
            for c in combines
        ],
    }
