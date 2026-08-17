"""Data export & deletion (PRD §9.2, docs/DATA_PRIVACY.md's engineering
checklist): a JSON export of everything a user has put into Debrief Golf,
and a real "delete my data" endpoint — a hard delete, not a soft/hidden
flag, per that checklist's explicit requirement.

Scope note: "spatial (shot/hole geometry)" in DATA_PRIVACY.md's wording
means the *shot* locations this user recorded, not `Hole`/`Course` rows —
those are shared reference geometry a real course's other players' rounds
may also reference, so deleting one user's account must not delete them.

`export_user_data` streams rather than building one dict (Phase 11's named
gap: this endpoint "returns every row the user owns, by definition," and
used to do that by loading every shot across every round — and every
practice shot across every session — into one Python structure before
FastAPI serialized any of it). It's now a generator, one round's (or
session's) rows fetched and yielded at a time and then dropped, so peak
memory is O(one round's shots) instead of O(every shot the user has ever
recorded). This is deliberately about memory, not latency — the query
count goes up (one extra small query per round/session rather than two
big ones), same trade the module docstring's DATA_PRIVACY.md commitment
already allows: the export exists and is complete, not that it's instant.
"""

import json
from collections.abc import Iterator

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep, clear_session_cookie
from app.models import (
    GarminConnection,
    PracticeSession,
    PracticeShot,
    Round,
    Shot,
    User,
    VirtualRound,
)

router = APIRouter()


def _round_shots(session: Session, round_id: int) -> list[dict]:
    """One round's shots, using a raw-column select rather than
    `select(Shot)` — geoalchemy2 hands back a non-JSON-serializable
    `WKBElement` for `location` on the ORM object, the same pitfall
    `GET /rounds/{id}/shots` already works around."""
    rows = session.exec(
        select(
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
        ).where(Shot.round_id == round_id)
    ).all()
    return [
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
        for r in rows
    ]


def _session_shots(session: Session, practice_session_id: int) -> list[dict]:
    shots = session.exec(
        select(PracticeShot).where(PracticeShot.session_id == practice_session_id)
    ).all()
    return [
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
        for shot in shots
    ]


def _stream_user_export(session: Session, user: User) -> Iterator[str]:
    user_id = user.id
    yield "{"

    yield '"user":' + json.dumps(
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "handicap_index": user.handicap_index,
            "created_at": user.created_at.isoformat(),
        }
    )

    garmin_connection = session.exec(
        select(GarminConnection).where(GarminConnection.user_id == user_id)
    ).first()
    yield ',"garmin_connected":' + json.dumps(garmin_connection is not None)

    yield ',"rounds":['
    for i, r in enumerate(
        session.exec(select(Round).where(Round.user_id == user_id).order_by(Round.played_at))
    ):
        yield ("," if i else "") + json.dumps(
            {
                "id": r.id,
                "played_at": r.played_at.isoformat(),
                "total_score": r.total_score,
                "status": r.status.value,
                "course_id": r.course_id,
                "shots": _round_shots(session, r.id),
            }
        )
    yield "]"

    yield ',"practice_sessions":['
    for i, s in enumerate(
        session.exec(
            select(PracticeSession)
            .where(PracticeSession.user_id == user_id)
            .order_by(PracticeSession.recorded_at)
        )
    ):
        yield ("," if i else "") + json.dumps(
            {
                "id": s.id,
                "source": s.source,
                "recorded_at": s.recorded_at.isoformat(),
                "shots": _session_shots(session, s.id),
            }
        )
    yield "]"

    virtual_rounds = session.exec(
        select(VirtualRound).where(VirtualRound.user_id == user_id)
    ).all()
    yield ',"virtual_rounds":' + json.dumps(
        [
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
        ]
    )

    yield "}"


@router.get("/me/export")
def export_user_data(user: CurrentUser, session: SessionDep) -> StreamingResponse:
    """A user's own data (GDPR/CCPA access & portability, DATA_PRIVACY.md):
    profile, rounds with their shots, R10/R50 practice sessions with their
    shots, and virtual rounds. Deliberately excludes the raw Garmin OAuth
    token strings — those are credentials this app holds on the user's
    behalf, not data *about* the user, so only connection status is
    included. Streamed (see module docstring) rather than assembled as one
    in-memory dict.
    """
    return StreamingResponse(
        _stream_user_export(session, user), media_type="application/json"
    )


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
