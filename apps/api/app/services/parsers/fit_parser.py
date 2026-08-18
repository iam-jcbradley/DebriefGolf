"""Garmin `.FIT` activity file parser (PRD §4.1, §4.3, §10 Phase 1).

Extracts a GPS point track and coarse activity metadata from Garmin Approach
watch/CT10 `.FIT` files, using `fitparse` to decode the binary format.

Scope note: this module does not attempt automatic shot segmentation from
the raw GPS track. No reliable public spec exists for per-shot golf messages
Garmin's watches may encode, and the PRD's "2-Minute Fast Audit" wizard
(Phase 3) is where a synced round's shots get verified/corrected by the
user anyway. `parse_fit_activity()` gives that wizard a `points` track and
round-level metadata to build against.

Per PRD §4.3: a `.FIT` file that can't be parsed at all, or that lacks
enough valid GPS coordinates to be a real round, is not rejected — it comes
back flagged `casual_practice` so it doesn't pollute Smart Bag baselines.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, BinaryIO, Protocol, cast

from fitparse import FitFile, FitParseError

from app.models import RoundStatus


class _FitMessage(Protocol):
    """`fitparse` ships no type stubs (no `py.typed`, no `.pyi` files), so
    `FitFile.get_messages()` comes back untyped — pyright falls back to
    `dict[str, Unknown] | DefinitionMessage`, neither of which it knows has
    `get_value`, even though every real message `fitparse` yields does at
    runtime. This is the actual, minimal interface this module uses."""

    def get_value(self, name: str) -> Any: ...

# Below this many valid GPS-tagged records, treat the file as not containing
# a real tracked round (PRD §4.3 "missing essential coordinates").
MIN_VALID_GPS_POINTS = 2

# FIT positions are encoded as "semicircles": degrees = semicircles * (180 / 2**31).
_SEMICIRCLES_TO_DEGREES = 180 / 2**31


@dataclass(frozen=True)
class GpsPoint:
    latitude: float
    longitude: float
    timestamp: datetime | None


@dataclass(frozen=True)
class FitParseResult:
    status: RoundStatus
    sport: str | None
    started_at: datetime | None
    points: list[GpsPoint] = field(default_factory=list)


def _semicircles_to_degrees(value: int) -> float:
    return value * _SEMICIRCLES_TO_DEGREES


def parse_fit_activity(source: str | bytes | BinaryIO) -> FitParseResult:
    """Parse a Garmin `.FIT` activity file into a GPS track + metadata.

    `source` is anything `fitparse.FitFile` accepts: a filesystem path, an
    open (seekable) file object, or raw bytes — e.g. an uploaded file's body.

    Never raises on a malformed/truncated file: parsing failures and
    insufficient GPS data both surface as `FitParseResult.status ==
    RoundStatus.casual_practice` with whatever (possibly empty) data was
    recovered before the failure, per PRD §4.3.
    """
    sport: str | None = None
    started_at: datetime | None = None
    points: list[GpsPoint] = []

    try:
        fit_file = FitFile(source)

        for mesg in cast(Iterable[_FitMessage], fit_file.get_messages("session")):
            sport = mesg.get_value("sport") or sport
            started_at = mesg.get_value("start_time") or started_at

        for mesg in cast(Iterable[_FitMessage], fit_file.get_messages("record")):
            lat_raw = mesg.get_value("position_lat")
            lng_raw = mesg.get_value("position_long")
            if lat_raw is None or lng_raw is None:
                continue
            points.append(
                GpsPoint(
                    latitude=_semicircles_to_degrees(lat_raw),
                    longitude=_semicircles_to_degrees(lng_raw),
                    timestamp=mesg.get_value("timestamp"),
                )
            )
    except (FitParseError, OSError):
        # Corrupted/truncated file — fall through with whatever we recovered;
        # the point-count check below will flag it casual_practice.
        pass

    status = (
        RoundStatus.needs_audit
        if len(points) >= MIN_VALID_GPS_POINTS
        else RoundStatus.casual_practice
    )
    return FitParseResult(status=status, sport=sport, started_at=started_at, points=points)
