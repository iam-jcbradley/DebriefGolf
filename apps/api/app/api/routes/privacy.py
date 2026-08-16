"""Data export & deletion (PRD §9.2, docs/DATA_PRIVACY.md's engineering
checklist): a JSON export of everything a user has put into Debrief Golf,
and a real "delete my data" endpoint — a hard delete, not a soft/hidden
flag, per that checklist's explicit requirement.

Scope note: "spatial (shot/hole geometry)" in DATA_PRIVACY.md's wording
means the *shot* locations this user recorded, not `Hole`/`Course` rows —
those are shared reference geometry a real course's other players' rounds
may also reference, so deleting one user's account must not delete them.
"""

from fastapi import APIRouter, Response
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep, clear_session_cookie
from app.models import (
    GarminConnection,
    PracticeSession,
    PracticeShot,
    Round,
    Shot,
    VirtualRound,
)

router = APIRouter()


def _serialize_shots(session: Session, user_id: int, round_ids: list[int]) -> dict[int, list[dict]]:
    """Shots grouped by round_id, using a raw-column select rather than
    `select(Shot)` — geoalchemy2 hands back a non-JSON-serializable
    `WKBElement` for `location` on the ORM object, the same pitfall
    `GET /rounds/{id}/shots` already works around."""
    if not round_ids:
        return {}
    rows = session.exec(
        select(
            Shot.round_id,
            Shot.id,
            Shot.hole_id,
            Shot.shot_number,
            Shot.club,
            Shot.start_lie,
            Shot.end_lie,
            Shot.start_distance_yards,
            Shot.end_distance_yards,
            Shot.strokes_gained,
            Shot.tag,
            func.ST_Y(Shot.location).label("lat"),
            func.ST_X(Shot.location).label("lng"),
        )
        .join(Round, Shot.round_id == Round.id)
        .where(Round.user_id == user_id)
    ).all()

    by_round: dict[int, list[dict]] = {round_id: [] for round_id in round_ids}
    for r in rows:
        by_round[r.round_id].append(
            {
                "id": r.id,
                "hole_id": r.hole_id,
                "shot_number": r.shot_number,
                "club": r.club,
                "start_lie": r.start_lie.value,
                "end_lie": r.end_lie.value,
                "start_distance_yards": r.start_distance_yards,
                "end_distance_yards": r.end_distance_yards,
                "strokes_gained": r.strokes_gained,
                "tag": r.tag,
                "location": {"lat": r.lat, "lng": r.lng} if r.lat is not None else None,
            }
        )
    return by_round


@router.get("/me/export")
def export_user_data(user: CurrentUser, session: SessionDep) -> dict:
    """A user's own data (GDPR/CCPA access & portability, DATA_PRIVACY.md):
    profile, rounds with their shots, R10/R50 practice sessions with their
    shots, and virtual rounds. Deliberately excludes the raw Garmin OAuth
    token strings — those are credentials this app holds on the user's
    behalf, not data *about* the user, so only connection status is
    included.
    """
    user_id = user.id
    rounds = list(
        session.exec(select(Round).where(Round.user_id == user_id).order_by(Round.played_at)).all()
    )
    shots_by_round = _serialize_shots(
        session, user_id, [r.id for r in rounds if r.id is not None]
    )

    practice_sessions = list(
        session.exec(
            select(PracticeSession)
            .where(PracticeSession.user_id == user_id)
            .order_by(PracticeSession.recorded_at)
        ).all()
    )
    practice_session_ids = [s.id for s in practice_sessions if s.id is not None]
    practice_shots_by_session: dict[int, list[dict]] = {sid: [] for sid in practice_session_ids}
    if practice_session_ids:
        for shot in session.exec(
            select(PracticeShot)
            .join(PracticeSession, PracticeShot.session_id == PracticeSession.id)
            .where(PracticeSession.user_id == user_id)
        ).all():
            practice_shots_by_session[shot.session_id].append(
                {
                    "id": shot.id,
                    "club": shot.club,
                    "club_speed_mph": shot.club_speed_mph,
                    "ball_speed_mph": shot.ball_speed_mph,
                    "smash_factor": shot.smash_factor,
                    "launch_angle_deg": shot.launch_angle_deg,
                    "spin_rate_rpm": shot.spin_rate_rpm,
                    "spin_axis_deg": shot.spin_axis_deg,
                    "club_path_deg": shot.club_path_deg,
                    "face_angle_deg": shot.face_angle_deg,
                    "carry_yards": shot.carry_yards,
                    "total_yards": shot.total_yards,
                    "captured_at": shot.captured_at.isoformat() if shot.captured_at else None,
                }
            )

    virtual_rounds = list(
        session.exec(select(VirtualRound).where(VirtualRound.user_id == user_id)).all()
    )
    garmin_connection = session.exec(
        select(GarminConnection).where(GarminConnection.user_id == user_id)
    ).first()

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "handicap_index": user.handicap_index,
            "created_at": user.created_at.isoformat(),
        },
        "garmin_connected": garmin_connection is not None,
        "rounds": [
            {
                "id": r.id,
                "played_at": r.played_at.isoformat(),
                "total_score": r.total_score,
                "status": r.status.value,
                "course_id": r.course_id,
                "shots": shots_by_round.get(r.id, []),
            }
            for r in rounds
        ],
        "practice_sessions": [
            {
                "id": s.id,
                "source": s.source,
                "recorded_at": s.recorded_at.isoformat(),
                "shots": practice_shots_by_session.get(s.id, []),
            }
            for s in practice_sessions
        ],
        "virtual_rounds": [
            {
                "id": v.id,
                "platform": v.platform.value,
                "course_name": v.course_name,
                "played_at": v.played_at.isoformat(),
                "holes_played": v.holes_played,
                "total_score": v.total_score,
                "notes": v.notes,
            }
            for v in virtual_rounds
        ],
    }


@router.delete("/me")
def delete_user_data(user: CurrentUser, session: SessionDep, response: Response) -> dict:
    """Real deletion (DATA_PRIVACY.md: "a real deletion..., not a
    soft/hidden flag") of everything this user owns: shots, rounds, R10/R50
    practice shots and sessions, virtual rounds, the Garmin OAuth
    connection, and the user row itself.
    """
    user_id = user.id

    # One statement. Every table that holds this user's data has an
    # ON DELETE CASCADE foreign key back to `user` (or to `round` /
    # `practice_session`, which cascade in turn) as of Phase 11, so Postgres
    # removes the children. This used to load every shot, round, practice
    # shot, practice session and virtual round into Python and delete them
    # one at a time in FK-safe order — correct, but O(everything the user
    # ever recorded) round trips, and a new child table would have silently
    # been missed.
    #
    # Shared reference data (`Course`/`Hole`, the SG benchmark table) has no
    # cascade to here by design: it isn't this user's data to delete, per
    # DATA_PRIVACY.md.
    session.delete(user)
    session.commit()

    clear_session_cookie(response)

    return {"deleted": True, "user_id": user_id}
