"""R10/R50 delivery profile aggregation (PRD §6.1, §10 Phase 6).

Aggregates `PracticeShot` rows — persisted from R10/R50 exports via
`app.services.parsers.launch_monitor_parser` — per club into delivery-number
averages (Club Path, Face Angle, derived Face-to-Path, Spin Axis, Smash
Factor, Carry), a session-by-session trend per club, and a Sim vs.
Real-World carry gapping delta against on-course Smart Bag numbers
(`app.services.smart_bag`).

Face-to-path is derived at read time (`face_angle_deg - club_path_deg`)
rather than stored on `PracticeShot`, since it's a pure function of the two
columns already there — Garmin's exports report path and face separately,
not the combined number.
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from app.models.practice import PracticeShot
from app.services.smart_bag import CLUB_ORDER, ClubGappingStats

_CLUB_RANK = {club: i for i, club in enumerate(CLUB_ORDER)}


def face_to_path_deg(shot: PracticeShot) -> float | None:
    if shot.face_angle_deg is None or shot.club_path_deg is None:
        return None
    return round(shot.face_angle_deg - shot.club_path_deg, 2)


def _avg(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 2) if values else None


def _present(values: list[float | None]) -> list[float]:
    return [v for v in values if v is not None]


@dataclass(frozen=True)
class ClubDeliveryProfile:
    club: str
    shot_count: int
    avg_club_path_deg: float | None
    avg_face_angle_deg: float | None
    avg_face_to_path_deg: float | None
    avg_spin_axis_deg: float | None
    avg_smash_factor: float | None
    avg_carry_yards: float | None


def _sort_by_club_order(clubs: list[str]) -> list[str]:
    return sorted(clubs, key=lambda c: _CLUB_RANK.get(c, len(CLUB_ORDER)))


def compute_delivery_profile(shots: list[PracticeShot]) -> list[ClubDeliveryProfile]:
    """One aggregate row per club, across every session passed in — callers
    decide the window (a single session, or every session on file)."""
    by_club: dict[str, list[PracticeShot]] = defaultdict(list)
    for shot in shots:
        by_club[shot.club].append(shot)

    profiles = [
        ClubDeliveryProfile(
            club=club,
            shot_count=len(club_shots),
            avg_club_path_deg=_avg(_present([s.club_path_deg for s in club_shots])),
            avg_face_angle_deg=_avg(_present([s.face_angle_deg for s in club_shots])),
            avg_face_to_path_deg=_avg(_present([face_to_path_deg(s) for s in club_shots])),
            avg_spin_axis_deg=_avg(_present([s.spin_axis_deg for s in club_shots])),
            avg_smash_factor=_avg(_present([s.smash_factor for s in club_shots])),
            avg_carry_yards=_avg(_present([s.carry_yards for s in club_shots])),
        )
        for club, club_shots in by_club.items()
    ]
    return sorted(profiles, key=lambda p: _CLUB_RANK.get(p.club, len(CLUB_ORDER)))


@dataclass(frozen=True)
class DeliveryTrendPoint:
    session_id: int
    recorded_at: datetime
    shot_count: int
    avg_carry_yards: float | None
    avg_smash_factor: float | None
    avg_face_to_path_deg: float | None
    avg_spin_axis_deg: float | None


@dataclass(frozen=True)
class SessionShotRow:
    session_id: int
    recorded_at: datetime
    shot: PracticeShot


def compute_delivery_trend(rows: list[SessionShotRow]) -> dict[str, list[DeliveryTrendPoint]]:
    """Per-club, per-session averages in chronological order — the "delivery
    profile trend over practice sessions" PRD §6.1 wants, for a line chart of
    (say) smash factor by session."""
    by_club_session: dict[str, dict[int, list[SessionShotRow]]] = defaultdict(
        lambda: defaultdict(list)
    )
    session_recorded_at: dict[int, datetime] = {}
    for row in rows:
        by_club_session[row.shot.club][row.session_id].append(row)
        session_recorded_at[row.session_id] = row.recorded_at

    trends: dict[str, list[DeliveryTrendPoint]] = {}
    for club, sessions in by_club_session.items():
        points = [
            DeliveryTrendPoint(
                session_id=session_id,
                recorded_at=session_recorded_at[session_id],
                shot_count=len(session_rows),
                avg_carry_yards=_avg(_present([r.shot.carry_yards for r in session_rows])),
                avg_smash_factor=_avg(_present([r.shot.smash_factor for r in session_rows])),
                avg_face_to_path_deg=_avg(
                    _present([face_to_path_deg(r.shot) for r in session_rows])
                ),
                avg_spin_axis_deg=_avg(_present([r.shot.spin_axis_deg for r in session_rows])),
            )
            for session_id, session_rows in sessions.items()
        ]
        points.sort(key=lambda p: p.recorded_at)
        trends[club] = points

    return {club: trends[club] for club in _sort_by_club_order(list(trends.keys()))}


@dataclass(frozen=True)
class GappingDelta:
    club: str
    range_carry_mean_yards: float | None
    on_course_carry_mean_yards: float | None
    delta_yards: float | None  # range minus on-course; positive = the range overstates carry


def compute_gapping_delta(
    range_profiles: list[ClubDeliveryProfile],
    on_course_stats: list[ClubGappingStats],
) -> list[GappingDelta]:
    """Sim vs. Real-World Gapping Delta (PRD §6.1): for each club with both a
    launch-monitor carry average and an on-course GPS-derived carry average
    (`app.services.smart_bag.shot_carry_distance`), how far apart are they?
    A club present in only one source still gets a row, with the missing
    side left `None` — a launch monitor session doesn't require having
    played that club on-course yet, and vice versa.
    """
    range_by_club = {
        p.club: p.avg_carry_yards for p in range_profiles if p.avg_carry_yards is not None
    }
    course_by_club = {
        s.club: round(s.carry.mean, 1) for s in on_course_stats if s.carry.count > 0
    }

    clubs = _sort_by_club_order(list(set(range_by_club) | set(course_by_club)))
    return [
        GappingDelta(
            club=club,
            range_carry_mean_yards=range_by_club.get(club),
            on_course_carry_mean_yards=course_by_club.get(club),
            delta_yards=(
                round(range_by_club[club] - course_by_club[club], 1)
                if club in range_by_club and club in course_by_club
                else None
            ),
        )
        for club in clubs
    ]
