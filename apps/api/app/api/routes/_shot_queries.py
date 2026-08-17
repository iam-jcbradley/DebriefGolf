"""Shared on-course-shot query helpers for `GET /bag` and `GET /practice/*`
(Phase 6, Phase 4's lateral dispersion; Phase 16's SQL push-down). Lives in
`app/api/routes/`, not `app/services/`, since these touch the database
session directly — see CLAUDE.md's layering note on why persistence stays
out of `services/`.

`club_gapping_with_lateral` exists to fix a real bug (found by the QA panel
gut-check, see docs/KNOWN_ISSUES.md): `practice.py`'s driver-dispersion
combine detector used to call `compute_club_gapping` without
`lateral_by_club`, so `ClubGappingStats.lateral` was always `None` and the
combine could never fire, while `bag.py`'s independent copy of the same
computation got it right. One function now, called from both, so a future
fix to this logic can't drift between the two call sites again.

`club_carry_dispersion_sql` is Phase 11's named gap: `GET /bag` and both
practice endpoints used to pull every on-course shot a user ever recorded
into Python just to compute per-club carry dispersion, ~200ms at 21,600
shots. Postgres's `percentile_cont` ordered-set aggregate computes the same
quartiles `numpy.percentile`'s default (linear-interpolation) method does,
so the ordering and the outlier fence it feeds
(`app/services/smart_bag.py`'s `reject_outliers_iqr`) can move into SQL
without changing which shots get rejected — verified to agree with the
Python implementation to a tight float tolerance in
`tests/test_shot_queries.py` (which sample gets excluded, and the exact
count, is exact; `avg()`/`percentile_cont()` vs. `statistics.fmean`/
`pstdev` aren't guaranteed the same summation order so those are compared
to `1e-9`, not `==`), on the same six-sample planted-outlier scenario
`tests/test_bag_route.py` already exercises against the live endpoint.
Lateral dispersion stays
in Python: it's a smaller query (only located shots) and pushing its
flat-earth trig into SQL would risk a third copy of
`app/services/geometry.py`'s `YARDS_PER_DEGREE_LAT` alongside the existing
TypeScript mirror.
"""

from sqlalchemy import case, func
from sqlmodel import Session, select

from app.core.orm_typing import col
from app.models import Hole, Round, Shot
from app.services.geometry import ShotGeometryRow, compute_lateral_by_club
from app.services.shot_view import ShotView
from app.services.smart_bag import (
    DEFAULT_IQR_MULTIPLIER,
    MIN_SAMPLES_FOR_IQR,
    ClubGappingStats,
    DispersionStats,
    build_club_gapping,
)


def fetch_on_course_shots(session: Session, user_id: int) -> list[ShotView]:
    """Every on-course shot this user has recorded, as raw columns rather
    than ORM objects — see app/services/shot_view.py for why."""
    return list(
        session.exec(
            select(  # type: ignore[reportCallIssue]
                Shot.club,
                Shot.start_distance_yards,
                Shot.end_distance_yards,
                Shot.end_lie,
                Shot.strokes_gained,
            )
            .join(Round, col(Shot.round_id) == Round.id)
            .where(Round.user_id == user_id)
        ).all()
    )


def fetch_shot_geometry_rows(session: Session, user_id: int) -> list[ShotGeometryRow]:
    """Every located on-course shot plus its hole's tee/green — the input
    `compute_lateral_by_club` needs to turn a GPS point into a lateral
    aim-line offset."""
    query = (
        select(  # type: ignore[reportCallIssue]
            Shot.club,
            func.ST_Y(Shot.location).label("shot_lat"),
            func.ST_X(Shot.location).label("shot_lng"),
            func.ST_Y(Hole.tee_location).label("tee_lat"),
            func.ST_X(Hole.tee_location).label("tee_lng"),
            func.ST_Y(Hole.green_center).label("green_lat"),
            func.ST_X(Hole.green_center).label("green_lng"),
        )
        .join(Hole, col(Shot.hole_id) == Hole.id)
        .join(Round, col(Shot.round_id) == Round.id)
        .where(Round.user_id == user_id)
        .where(col(Shot.club).is_not(None))
        .where(col(Shot.location).is_not(None))
        .where(col(Hole.tee_location).is_not(None))
        .where(col(Hole.green_center).is_not(None))
    )
    return [ShotGeometryRow(**row._mapping) for row in session.exec(query)]


def club_carry_dispersion_sql(
    session: Session, user_id: int, k: float = DEFAULT_IQR_MULTIPLIER
) -> dict[str, DispersionStats]:
    """Per-club carry-distance dispersion, IQR outlier rejection included,
    computed entirely in SQL rather than by walking every shot into Python.

    Mirrors `app/services/smart_bag.py`'s `reject_outliers_iqr` +
    `compute_dispersion` in three CTEs: `carries` is one row per full-swing
    shot's carry distance (`start - end`, filtered to non-empty,
    non-putter clubs with a positive carry — the same full-swing-shot
    definition the pre-Phase-16 Python walk used); `quartiles` computes each
    club's Q1/Q3 with `percentile_cont`, the same linear-interpolation
    method `numpy.percentile`'s default uses; `bounds` turns those into the
    Tukey fence (skipped — `lower`/`upper` left `NULL` — for clubs below
    `MIN_SAMPLES_FOR_IQR`, same as the Python version returning samples
    unchanged). The final query aggregates `carries` with a `FILTER` for
    "inside the fence, or there was no fence", which is exactly what the
    Python version does in a second list comprehension.
    """
    carry_expr = col(Shot.start_distance_yards) - col(Shot.end_distance_yards)
    carries = (
        select(col(Shot.club).label("club"), carry_expr.label("carry"))
        .join(Round, col(Shot.round_id) == Round.id)
        .where(Round.user_id == user_id)
        # A club of "" is as much "no club recorded" as NULL is, so both
        # get excluded here, not just NULL.
        .where(col(Shot.club).is_not(None))
        .where(Shot.club != "")
        .where(Shot.club != "Putter")
        .where(carry_expr > 0)
    ).cte("carries")

    quartiles = (
        select(
            carries.c.club,
            func.count().label("n"),
            func.percentile_cont(0.25).within_group(carries.c.carry).label("q1"),
            func.percentile_cont(0.75).within_group(carries.c.carry).label("q3"),
        )
        .group_by(carries.c.club)
    ).cte("quartiles")

    iqr = quartiles.c.q3 - quartiles.c.q1
    lower = case((quartiles.c.n >= MIN_SAMPLES_FOR_IQR, quartiles.c.q1 - k * iqr), else_=None)
    upper = case((quartiles.c.n >= MIN_SAMPLES_FOR_IQR, quartiles.c.q3 + k * iqr), else_=None)
    bounds = select(
        quartiles.c.club, quartiles.c.n, lower.label("lower"), upper.label("upper")
    ).cte("bounds")

    kept = carries.c.carry.between(bounds.c.lower, bounds.c.upper) | bounds.c.lower.is_(None)

    query = (
        select(  # type: ignore[reportCallIssue]
            carries.c.club,
            func.count().filter(kept).label("count"),
            func.avg(carries.c.carry).filter(kept).label("mean"),
            func.percentile_cont(0.5).within_group(carries.c.carry).filter(kept).label("median"),
            func.stddev_pop(carries.c.carry).filter(kept).label("stdev"),
            (bounds.c.n - func.count().filter(kept)).label("excluded_outliers"),
        )
        .select_from(carries.join(bounds, carries.c.club == bounds.c.club))
        .group_by(carries.c.club, bounds.c.n)
    )

    return {
        row.club: DispersionStats(
            count=row.count,
            mean=float(row.mean) if row.mean is not None else 0.0,
            median=float(row.median) if row.median is not None else 0.0,
            stdev=float(row.stdev) if row.stdev is not None else 0.0,
            excluded_outliers=row.excluded_outliers,
        )
        for row in session.exec(query)
    }


def club_gapping_with_lateral(session: Session, user_id: int) -> list[ClubGappingStats]:
    """Carry *and* lateral dispersion per club: carry from the SQL
    push-down above, lateral from the smaller geometry-joined query (only
    located shots need it)."""
    carry_by_club = club_carry_dispersion_sql(session, user_id)
    lateral_by_club = compute_lateral_by_club(fetch_shot_geometry_rows(session, user_id))
    return build_club_gapping(carry_by_club, lateral_by_club=lateral_by_club)
