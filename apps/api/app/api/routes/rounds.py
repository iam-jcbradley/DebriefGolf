import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User
from app.services.approach import classify_approach_leave
from app.services.parsers.fit_parser import parse_fit_activity
from app.services.putting import evaluate_putting
from app.services.strokes_gained import compute_round_strokes_gained
from app.services.tiger_five import evaluate_round

router = APIRouter()


@router.get("/rounds")
def list_rounds(session: Annotated[Session, Depends(get_session)]) -> list[Round]:
    return list(session.exec(select(Round)).all())


class RoundCreateIn(BaseModel):
    user_id: int
    course_id: int
    played_at: datetime | None = None
    total_score: int | None = None
    status: RoundStatus = RoundStatus.needs_audit


@router.post("/rounds", status_code=201)
def create_round(
    payload: RoundCreateIn, session: Annotated[Session, Depends(get_session)]
) -> Round:
    """General round creation (PRD §10 Phase 5) — unlike `POST
    /rounds/upload`, this isn't tied to a `.FIT` file: it's for a round
    entered by hand (against a course that already exists, manually built
    or sourced from OSM via `POST /courses`), which is now the primary way
    round data gets in at all since Garmin's OAuth API (Phase 3) turned out
    to require a paid developer account.
    """
    if session.get(User, payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if session.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    round_ = Round(
        user_id=payload.user_id,
        course_id=payload.course_id,
        played_at=payload.played_at or datetime.now(UTC),
        total_score=payload.total_score,
        status=payload.status,
    )
    session.add(round_)
    session.commit()
    session.refresh(round_)
    return round_


class ShotLocationIn(BaseModel):
    lat: float
    lng: float


class ShotCreateIn(BaseModel):
    hole_number: int
    shot_number: int
    club: str | None = None
    start_lie: Lie
    end_lie: Lie
    start_distance_yards: float
    end_distance_yards: float
    location: ShotLocationIn | None = None
    tag: str | None = None


class BulkShotsIn(BaseModel):
    shots: list[ShotCreateIn]


@router.post("/rounds/{round_id}/shots/bulk", status_code=201)
def create_shots_bulk(
    round_id: int, payload: BulkShotsIn, session: Annotated[Session, Depends(get_session)]
) -> list[dict]:
    """Adds shots to a round in one call (PRD §10 Phase 5) — the manual
    entry flow accumulates a hole's shots client-side (same `DraftShot`
    pattern the Phase 3 audit wizard already built, including its optional
    GPS `location` picked on the hole map) and submits them here once the
    user is done with a hole or the whole round. Purely additive: calling
    this twice for the same round creates two sets of shots, it doesn't
    replace anything — there's no manual-entry "edit a submitted round" flow
    yet.
    """
    round_ = session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if round_.course_id is None:
        raise HTTPException(status_code=409, detail="Round has no course assigned yet")

    holes = session.exec(select(Hole).where(Hole.course_id == round_.course_id)).all()
    hole_id_by_number = {hole.number: hole.id for hole in holes}

    unknown_numbers = sorted({s.hole_number for s in payload.shots} - hole_id_by_number.keys())
    if unknown_numbers:
        raise HTTPException(
            status_code=422,
            detail=f"Round's course has no hole(s) numbered {unknown_numbers}",
        )

    created: list[tuple[Shot, ShotCreateIn]] = []
    for s in payload.shots:
        shot = Shot(
            round_id=round_id,
            hole_id=hole_id_by_number[s.hole_number],
            shot_number=s.shot_number,
            club=s.club,
            start_lie=s.start_lie,
            end_lie=s.end_lie,
            start_distance_yards=s.start_distance_yards,
            end_distance_yards=s.end_distance_yards,
            location=(
                WKTElement(f"POINT({s.location.lng} {s.location.lat})", srid=4326)
                if s.location
                else None
            ),
            tag=s.tag,
        )
        session.add(shot)
        created.append((shot, s))
    session.commit()

    # Built from `shot.id` plus the already-known request payload, not by
    # re-reading `shot.location` off the refreshed ORM object — geoalchemy2
    # hands that back as a `WKBElement`, which isn't JSON-serializable (see
    # the same fix on `GET /rounds/{round_id}/shots` above).
    result = []
    for shot, s in created:
        session.refresh(shot)
        result.append(
            {
                "id": shot.id,
                "hole_id": shot.hole_id,
                "shot_number": s.shot_number,
                "club": s.club,
                "start_lie": s.start_lie.value,
                "end_lie": s.end_lie.value,
                "start_distance_yards": s.start_distance_yards,
                "end_distance_yards": s.end_distance_yards,
                "strokes_gained": shot.strokes_gained,
                "tag": s.tag,
                "location": {"lat": s.location.lat, "lng": s.location.lng} if s.location else None,
            }
        )
    return result


@router.post("/rounds/upload")
async def upload_fit_activity(
    user_id: int, file: UploadFile, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Ingest a Garmin `.FIT` activity file (PRD §4.1, §10 Phase 3): parses
    it with `app.services.parsers.fit_parser`, then creates a `Round` with
    no course or shots yet — course assignment and shot entry happen in the
    audit wizard. Per PRD §4.3, a corrupted or coordinate-sparse file still
    creates a round (flagged `casual_practice`), it isn't rejected.
    """
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    contents = await file.read()
    result = parse_fit_activity(contents)

    round_ = Round(
        user_id=user_id,
        played_at=result.started_at or datetime.now(UTC),
        status=result.status,
    )
    session.add(round_)
    session.commit()
    session.refresh(round_)

    return {
        "round_id": round_.id,
        "status": round_.status.value,
        "sport": result.sport,
        "point_count": len(result.points),
    }


@router.get("/rounds/{round_id}/shots")
def list_round_shots(
    round_id: int, session: Annotated[Session, Depends(get_session)]
) -> list[dict]:
    round_ = session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")

    # Selecting raw columns (rather than `select(Shot)`) avoids handing back
    # geoalchemy2's `WKBElement` for `location` — it isn't JSON-serializable,
    # so a plain `list[Shot]` response crashes on any shot with a GPS point.
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
        )
        .where(Shot.round_id == round_id)
        .order_by(Shot.id)
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
    if not shots:
        # A freshly-uploaded .FIT round (see POST /rounds/upload) has GPS
        # points but no recorded shots yet — nothing to compute until it's
        # been through the audit wizard.
        return {
            "round_id": round_id,
            "status": round_.status.value,
            "needs_shots": True,
        }

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


@router.get("/rounds/{round_id}/holes")
def list_round_holes(
    round_id: int, session: Annotated[Session, Depends(get_session)]
) -> list[dict]:
    """Hole summaries for a round's course (PRD §10 Phase 4), for a hole
    picker in the hole-replay UI. Empty for a round with no course assigned
    yet (see POST /rounds/upload)."""
    round_ = session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if round_.course_id is None:
        return []

    holes = session.exec(
        select(Hole).where(Hole.course_id == round_.course_id).order_by(Hole.number)
    ).all()

    shot_counts: dict[int, int] = defaultdict(int)
    for shot in session.exec(select(Shot).where(Shot.round_id == round_id)).all():
        shot_counts[shot.hole_id] += 1

    return [
        {
            "hole_number": hole.number,
            "par": hole.par,
            "yardage": hole.yardage,
            "shot_count": shot_counts.get(hole.id, 0),
        }
        for hole in holes
    ]


@router.get("/rounds/{round_id}/holes/{hole_number}/replay")
def get_hole_replay(
    round_id: int, hole_number: int, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Hole geometry + this round's shots on that hole, for the hole replay
    map (PRD §5.3, §10 Phase 4). Includes each shot's `approach_leave`
    classification (PRD §5.2) so the frontend can raise a short-sided /
    "sucker pin" strategy banner without recomputing it.
    """
    round_ = session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if round_.course_id is None:
        raise HTTPException(status_code=409, detail="Round has no course assigned yet")

    hole = session.exec(
        select(Hole).where(Hole.course_id == round_.course_id, Hole.number == hole_number)
    ).first()
    if hole is None:
        raise HTTPException(status_code=404, detail="Hole not found")

    geo = session.exec(
        select(
            func.ST_Y(Hole.tee_location).label("tee_lat"),
            func.ST_X(Hole.tee_location).label("tee_lng"),
            func.ST_Y(Hole.green_center).label("green_lat"),
            func.ST_X(Hole.green_center).label("green_lng"),
            func.ST_AsGeoJSON(Hole.green_boundary).label("green_boundary_geojson"),
        ).where(Hole.id == hole.id)
    ).first()

    green_boundary = None
    if geo and geo.green_boundary_geojson:
        ring = json.loads(geo.green_boundary_geojson)["coordinates"][0]
        green_boundary = [{"lat": lat, "lng": lng} for lng, lat in ring]

    shots = list(
        session.exec(
            select(Shot)
            .where(Shot.round_id == round_id, Shot.hole_id == hole.id)
            .order_by(Shot.shot_number)
        ).all()
    )

    shot_locations: dict[int, dict] = {}
    if shots:
        location_rows = session.exec(
            select(
                Shot.id,
                func.ST_Y(Shot.location).label("lat"),
                func.ST_X(Shot.location).label("lng"),
            ).where(
                Shot.hole_id == hole.id, Shot.round_id == round_id, Shot.location.is_not(None)
            )
        ).all()
        shot_locations = {row.id: {"lat": row.lat, "lng": row.lng} for row in location_rows}

    shot_payloads = [
        {
            "shot_id": shot.id,
            "shot_number": shot.shot_number,
            "club": shot.club,
            "start_lie": shot.start_lie.value,
            "end_lie": shot.end_lie.value,
            "start_distance_yards": shot.start_distance_yards,
            "end_distance_yards": shot.end_distance_yards,
            "strokes_gained": shot.strokes_gained,
            "tag": shot.tag,
            "approach_leave": classify_approach_leave(shot).value,
            "location": shot_locations.get(shot.id),
        }
        for shot in shots
    ]

    return {
        "round_id": round_id,
        "hole_number": hole.number,
        "par": hole.par,
        "yardage": hole.yardage,
        "tee": (
            {"lat": geo.tee_lat, "lng": geo.tee_lng} if geo and geo.tee_lat is not None else None
        ),
        "green_center": (
            {"lat": geo.green_lat, "lng": geo.green_lng}
            if geo and geo.green_lat is not None
            else None
        ),
        "green_boundary": green_boundary,
        "shots": shot_payloads,
        "short_sided_count": sum(
            1 for s in shot_payloads if s["approach_leave"] == "short_sided"
        ),
    }
