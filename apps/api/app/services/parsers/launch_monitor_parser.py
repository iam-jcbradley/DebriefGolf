"""Approach R10/R50 launch monitor CSV/JSON export parser (PRD §4.1, §6.1, §10 Phase 1).

Garmin doesn't publish a fixed schema for R10/R50 practice-session exports,
and header wording/units vary across app versions and export formats. This
parser normalizes headers (case/punctuation/whitespace-insensitive) against
a set of known aliases per field (`_ALIASES`) rather than requiring exact
column names, so it tolerates the header variance a real export is likely
to have.

Malformed rows don't abort the whole file: `parse_launch_monitor_csv()` and
`parse_launch_monitor_json()` return every row that parsed successfully
alongside a list of per-row error messages, so one bad row in an otherwise
good session export doesn't lose the rest.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import IO, Any

# canonical field name -> accepted header spellings (matched after normalization)
_ALIASES: dict[str, list[str]] = {
    "club": ["club", "club type", "club name"],
    "club_speed_mph": ["club speed", "club speed mph", "clubspeed"],
    "ball_speed_mph": ["ball speed", "ball speed mph", "ballspeed"],
    "smash_factor": ["smash factor", "smash", "efficiency"],
    "launch_angle_deg": ["launch angle", "launch angle deg", "vla", "vertical launch angle"],
    "spin_rate_rpm": ["spin rate", "spin rate rpm", "backspin", "total spin"],
    "spin_axis_deg": ["spin axis", "spin axis deg", "sidespin axis"],
    "club_path_deg": ["club path", "club path deg", "path"],
    "face_angle_deg": ["face angle", "face angle deg", "face to target", "face to path"],
    "carry_yards": ["carry", "carry distance", "carry yds", "carry yards"],
    "total_yards": ["total distance", "total", "total yds", "total yards", "carry + roll"],
    "captured_at": ["date", "timestamp", "time", "date time"],
}

_MISSING_TOKENS = {"", "-", "--", "n/a", "na", "null", "none"}

_DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y-%m-%d",
    "%m/%d/%Y",
]


def _normalize(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


_NORMALIZED_ALIASES: dict[str, set[str]] = {
    canonical: {_normalize(alias) for alias in aliases} for canonical, aliases in _ALIASES.items()
}


@dataclass(frozen=True)
class LaunchMonitorShot:
    club: str
    club_speed_mph: float | None
    ball_speed_mph: float | None
    smash_factor: float | None
    launch_angle_deg: float | None
    spin_rate_rpm: float | None
    spin_axis_deg: float | None
    club_path_deg: float | None
    face_angle_deg: float | None
    carry_yards: float | None
    total_yards: float | None
    captured_at: datetime | None


@dataclass(frozen=True)
class LaunchMonitorParseResult:
    shots: list[LaunchMonitorShot] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class _RowError(Exception):
    pass


def _build_column_map(headers: list[str]) -> dict[str, str]:
    """canonical field name -> the actual header string it matched, for
    whichever of `_ALIASES`'s fields are present in `headers`."""
    column_map: dict[str, str] = {}
    for header in headers:
        normalized = _normalize(header)
        for canonical, aliases in _NORMALIZED_ALIASES.items():
            if canonical not in column_map and normalized in aliases:
                column_map[canonical] = header
                break
    return column_map


def _parse_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if cleaned.lower() in _MISSING_TOKENS:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    cleaned = raw.strip()
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _row_to_shot(row: dict[str, str], column_map: dict[str, str]) -> LaunchMonitorShot:
    club = (row.get(column_map.get("club", ""), "") or "").strip()
    if not club:
        raise _RowError("missing required field 'club'")

    def get_float(canonical: str) -> float | None:
        header = column_map.get(canonical)
        if header is None:
            return None
        return _parse_float(row.get(header))

    club_speed = get_float("club_speed_mph")
    ball_speed = get_float("ball_speed_mph")
    smash_factor = get_float("smash_factor")
    if smash_factor is None and club_speed and ball_speed:
        smash_factor = round(ball_speed / club_speed, 3)

    carry_yards = get_float("carry_yards")
    total_yards = get_float("total_yards")
    if carry_yards is None and total_yards is None:
        raise _RowError("missing both carry and total distance")

    return LaunchMonitorShot(
        club=club,
        club_speed_mph=club_speed,
        ball_speed_mph=ball_speed,
        smash_factor=smash_factor,
        launch_angle_deg=get_float("launch_angle_deg"),
        spin_rate_rpm=get_float("spin_rate_rpm"),
        spin_axis_deg=get_float("spin_axis_deg"),
        club_path_deg=get_float("club_path_deg"),
        face_angle_deg=get_float("face_angle_deg"),
        carry_yards=carry_yards,
        total_yards=total_yards,
        captured_at=_parse_datetime(row.get(column_map.get("captured_at", ""))),
    )


def _read_text(source: str | bytes | IO) -> str:
    if isinstance(source, bytes):
        return source.decode("utf-8-sig")
    if isinstance(source, str):
        return source
    content = source.read()
    return content.decode("utf-8-sig") if isinstance(content, bytes) else content


def parse_launch_monitor_csv(source: str | bytes | IO) -> LaunchMonitorParseResult:
    """Parse an R10/R50 CSV export. `source` is CSV text, raw bytes, or an
    open file object — not a filesystem path."""
    text = _read_text(source)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return LaunchMonitorParseResult(errors=["CSV has no header row"])

    column_map = _build_column_map(list(reader.fieldnames))
    shots: list[LaunchMonitorShot] = []
    errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            shots.append(_row_to_shot(row, column_map))
        except _RowError as exc:
            errors.append(f"row {line_number}: {exc}")
    return LaunchMonitorParseResult(shots=shots, errors=errors)


def parse_launch_monitor_json(source: str | bytes) -> LaunchMonitorParseResult:
    """Parse an R10/R50 JSON export: either a bare array of shot objects, or
    an object with a `shots`/`data` array."""
    text = source.decode("utf-8-sig") if isinstance(source, bytes) else source
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        return LaunchMonitorParseResult(errors=[f"invalid JSON: {exc}"])

    if isinstance(data, dict):
        records = data.get("shots", data.get("data", []))
    elif isinstance(data, list):
        records = data
    else:
        records = []

    if not records:
        return LaunchMonitorParseResult(errors=["no shot records found in JSON"])

    shots: list[LaunchMonitorShot] = []
    errors: list[str] = []
    for i, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"record {i}: expected an object, got {type(record).__name__}")
            continue
        # JSON values may be numbers/bools/None rather than strings; the row
        # parser (shared with CSV) works on strings, so stringify uniformly.
        string_row = {k: ("" if v is None else str(v)) for k, v in record.items()}
        column_map = _build_column_map(list(string_row.keys()))
        try:
            shots.append(_row_to_shot(string_row, column_map))
        except _RowError as exc:
            errors.append(f"record {i}: {exc}")
    return LaunchMonitorParseResult(shots=shots, errors=errors)
