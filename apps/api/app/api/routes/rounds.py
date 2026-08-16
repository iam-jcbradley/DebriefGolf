import json
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, UploadFile
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel
from sqlalchemy import bindparam, func, update
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep
from app.api.uploads import read_upload
from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User
from app.services.approach import classify_approach_leave
from app.services.parsers.fit_parser import parse_fit_activity
from app.services.putting import evaluate_putting
from app.services.strokes_gained import compute_round_strokes_gained
from app.services.tiger_five import evaluate_round

router = APIRouter()


def _owned_round(round_id: int, user: User, session: Session) -> Round:
    """The round, or 404.

    404 rather than 403 for a round belonging to someone else: a 403 would
    confirm that a round with this id exists and is simply not yours, which
    is more than a stranger should be able to learn by guessing integers.
    """
    round_ = session.get(Round, round_id)
    if round_ is None or round_.user_id != user.id:
        raise HTTPException(status_code=404, detail="Round not found")
    return round_


def _persist_round_strokes_gained(session: Session, round_id: int, handicap_index: float) -> None:
    """Recomputes and stores `Shot.strokes_gained` for one round.

    The stored column is what `GET /practice/combines`, the export and the
    hole replay all read. It's written here — when shots are recorded — and
    when the owner's handicap index changes, rather than on every analytics
    read, which is what it used to be.
    """
    shots = list(
        session.exec(select(Shot).where(Shot.round_id == round_id).order_by(Shot.id)).all()
    )
    if not shots:
        return

    holes = {
        hole.id: hole
        for hole in session.exec(
            select(Hole).join(Round, Hole.course_id == Round.course_id).where(Round.id == round_id)
        ).all()
    }
    if not all(shot.hole_id in holes for shot in shots):
        # A shot whose hole isn't on the round's current course — nothing
        # coherent to compute against. Leave the column alone.
        return

    summary = compute_round_strokes_gained(
        [(shot, holes[shot.hole_id].par) for shot in shots], handicap_index
    )

    # One executemany rather than a statement per shot. Deliberately against
    # the Core table rather than the ORM entity: `session.execute(update(Shot),
    # [rows])` is interpreted as an ORM bulk-update-by-primary-key and demands
    # an `id` in every row, which isn't the statement wanted here.
    shot_table = Shot.__table__
    session.execute(
        update(shot_table)
        .where(shot_table.c.id == bindparam("b_id"))
        .values(strokes_gained=bindparam("b_sg")),
        [{"b_id": r.shot_id, "b_sg": r.strokes_gained} for r in summary.shots if r.shot_id],
    )
    session.commit()


def refresh_user_strokes_gained(session: Session, user: User) -> None:
    """Recomputes stored SG across every round this user has played.

    Called when their handicap index changes (`PATCH /api/auth/me`), since
    the SG benchmark bucket is derived from it — without this, the stored
    values silently describe the handicap they used to have.
    """
    for round_id in session.exec(select(Round.id).where(Round.user_id == user.id)).all():
        _persist_round_strokes_gained(session, round_id, user.handicap_index)


# Enough for a season of golf in one response, small enough that nobody
# accidentally serializes a decade of rounds to render "your latest round".
DEFAULT_ROUND_LIMIT = 50
MAX_ROUND_LIMIT = 200


@router.get("/rounds")
def list_rounds(
    user: CurrentUser,
    session: SessionDep,
    limit: int = DEFAULT_ROUND_LIMIT,
    offset: int = 0,
) -> list[Round]:
    """This user's rounds, most recent first.

    Paginated as of Phase 11: this was unbounded, and the dashboard fetched
    *every* round only to sort them client-side and use the newest one — so
    the cost of loading the front page grew with every round ever played.
    It now asks for `?limit=1`.

    Until Phase 10 the `user_id` filter was optional too, so an unfiltered
    call returned every round in the database, which is what once let the
    dashboard show whichever player's round happened to be newest globally.
    """
    if limit < 1 or limit > MAX_ROUND_LIMIT:
        raise HTTPException(
            status_code=422, detail=f"limit must be between 1 and {MAX_ROUND_LIMIT}"
        )
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must not be negative")

    return list(
        session.exec(
            select(Round)
            .where(Round.user_id == user.id)
            .order_by(Round.played_at.desc(), Round.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


class RoundCreateIn(BaseModel):
    course_id: int
    played_at: datetime | None = None
    total_score: int | None = None
    status: RoundStatus = RoundStatus.needs_audit


@router.post("/rounds", status_code=201)
def create_round(payload: RoundCreateIn, user: CurrentUser, session: SessionDep) -> Round:
    """General round creation (PRD §10 Phase 5) — unlike `POST
    /rounds/upload`, this isn't tied to a `.FIT` file: it's for a round
    entered by hand (against a course that already exists, manually built
    or sourced from OSM via `POST /courses`), which is now the primary way
    round data gets in at all since Garmin's OAuth API (Phase 3) turned out
    to require a paid developer account.
    """
    if session.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    round_ = Round(
        user_id=user.id,
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
    round_id: int, payload: BulkShotsIn, user: CurrentUser, session: SessionDep
) -> list[dict]:
    """Adds shots to a round in one call (PRD §10 Phase 5) — the manual
    entry flow accumulates a hole's shots client-side (same `DraftShot`
    pattern the Phase 3 audit wizard already built, including its optional
    GPS `location` picked on the hole map) and submits them here once the
    user is done with a hole or the whole round.

    Idempotent on `(round_id, hole_id, shot_number)` — a hole's shot 1,
    shot 2, ... is a natural key (`Shot.__table_args__`), so a retried
    submit (a dropped connection after the write actually went through,
    same shot resubmitted) returns the shot that's already there instead of
    creating a duplicate or erroring. It's still purely additive in the
    sense that matters: there's no way to *edit* a previously-submitted
    shot's club/lie/distances through this endpoint, only to (harmlessly)
    resubmit it unchanged.
    """
    round_ = _owned_round(round_id, user, session)
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

    existing_by_key = {
        (shot.hole_id, shot.shot_number): shot
        for shot in session.exec(select(Shot).where(Shot.round_id == round_id)).all()
    }

    result_pairs: list[tuple[Shot, ShotCreateIn]] = []
    for s in payload.shots:
        key = (hole_id_by_number[s.hole_number], s.shot_number)
        existing = existing_by_key.get(key)
        if existing is not None:
            result_pairs.append((existing, s))
            continue
        shot = Shot(
            round_id=round_id,
            hole_id=key[0],
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
        # Guards a duplicate *within this same payload* too, not just
        # against what was already in the database.
        existing_by_key[key] = shot
        result_pairs.append((shot, s))
    session.commit()

    # Built from `shot.id` plus the already-known request payload, not by
    # re-reading `shot.location` off the refreshed ORM object — geoalchemy2
    # hands that back as a `WKBElement`, which isn't JSON-serializable (see
    # the same fix on `GET /rounds/{round_id}/shots` above). For a reused
    # (already-existing) shot this reports the *incoming* payload's values
    # rather than re-reading the stored row — correct for a true retry
    # (they're identical), and simplest for a client that resubmits
    # something slightly different: no edit path exists here to honor that
    # difference anyway, this endpoint just doesn't silently duplicate it.
    _persist_round_strokes_gained(session, round_id, user.handicap_index)

    result = []
    for shot, s in result_pairs:
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
    file: UploadFile, request: Request, user: CurrentUser, session: SessionDep
) -> dict:
    """Ingest a Garmin `.FIT` activity file (PRD §4.1, §10 Phase 3): parses
    it with `app.services.parsers.fit_parser`, then creates a `Round` with
    no course or shots yet — course assignment and shot entry happen in the
    audit wizard. Per PRD §4.3, a corrupted or coordinate-sparse file still
    creates a round (flagged `casual_practice`), it isn't rejected.
    """
    contents = await read_upload(file, request)
    result = parse_fit_activity(contents)

    round_ = Round(
        user_id=user.id,
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
    round_id: int, user: CurrentUser, session: SessionDep
) -> list[dict]:
    _owned_round(round_id, user, session)  # 404s unless this round is the caller's

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
    round_id: int, user: CurrentUser, session: SessionDep
) -> dict:
    """Round-level diagnostics (PRD §5, §8): Strokes Gained by category,
    Tiger 5 violations + Clean Card Index, putting mechanics, and a
    per-shot breakdown. Also persists the computed `Shot.strokes_gained`
    back onto each shot.
    """
    round_ = _owned_round(round_id, user, session)

    handicap_index = user.handicap_index

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
    if not all(shot.hole_id in holes for shot in shots):
        # The round's course changed (audit wizard correction, manual
        # reassignment) after these shots were recorded against the old
        # one's holes — Hole rows are shared reference geometry and aren't
        # deleted when that happens, so the FK is still valid, just stale.
        # `holes[shot.hole_id]` below would KeyError; a 409 says plainly
        # what's wrong instead. Same mismatch `_persist_round_strokes_gained`
        # already treats as a no-op rather than crash.
        raise HTTPException(
            status_code=409,
            detail="This round's course has changed since some of its shots were recorded. "
            "Reassign the correct course, or re-run the audit wizard, before viewing analytics.",
        )

    sg_summary = compute_round_strokes_gained(
        [(shot, holes[shot.hole_id].par) for shot in shots], handicap_index
    )

    # Read-only. This used to write the computed SG back onto every shot in
    # the round and commit — a GET that mutated the database on the
    # dashboard's hot path, non-idempotent and taking a write lock on every
    # load. The values are persisted when shots are recorded instead (see
    # `_persist_round_strokes_gained`); Tiger 5 gets them passed in rather
    # than reading them off ORM objects this endpoint had to mutate first.
    sg_by_shot_id = {r.shot_id: r.strokes_gained for r in sg_summary.shots}

    shots_by_hole: dict[int, list[Shot]] = defaultdict(list)
    for shot in shots:
        shots_by_hole[shot.hole_id].append(shot)
    tiger_five = evaluate_round(
        [
            (holes[hole_id].number, holes[hole_id].par, hole_shots)
            for hole_id, hole_shots in shots_by_hole.items()
        ],
        strokes_gained=sg_by_shot_id,
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
    round_id: int, user: CurrentUser, session: SessionDep
) -> list[dict]:
    """Hole summaries for a round's course (PRD §10 Phase 4), for a hole
    picker in the hole-replay UI. Empty for a round with no course assigned
    yet (see POST /rounds/upload)."""
    round_ = _owned_round(round_id, user, session)
    if round_.course_id is None:
        return []

    holes = session.exec(
        select(Hole).where(Hole.course_id == round_.course_id).order_by(Hole.number)
    ).all()

    # GROUP BY rather than loading every shot in the round to count them in
    # Python — this endpoint only ever needed the counts.
    shot_counts = {
        hole_id: count
        for hole_id, count in session.exec(
            select(Shot.hole_id, func.count())
            .where(Shot.round_id == round_id)
            .group_by(Shot.hole_id)
        ).all()
    }

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
    round_id: int, hole_number: int, user: CurrentUser, session: SessionDep
) -> dict:
    """Hole geometry + this round's shots on that hole, for the hole replay
    map (PRD §5.3, §10 Phase 4). Includes each shot's `approach_leave`
    classification (PRD §5.2) so the frontend can raise a short-sided /
    "sucker pin" strategy banner without recomputing it.
    """
    round_ = _owned_round(round_id, user, session)
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
