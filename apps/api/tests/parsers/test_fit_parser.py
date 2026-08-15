"""Tests for `app.services.parsers.fit_parser`.

The "valid" case mocks `fitparse.FitFile` rather than reading a real binary
`.FIT` fixture: fitparse's binary decoding is a well-tested third-party
concern, and hand-crafting a byte-correct `.FIT` file (headers, CRC,
per-message field definitions) without a real Garmin export to base it on
risks testing our own encoding bugs rather than the parser's extraction
logic. Mocking lets us assert exactly how `parse_fit_activity` turns
`fitparse` messages into `GpsPoint`s/metadata, which is the code we own.

The "corrupted" case uses a real (deliberately invalid) fixture file on
disk, so it genuinely exercises `fitparse`'s own error path.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models import RoundStatus
from app.services.parsers.fit_parser import GpsPoint, parse_fit_activity

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class _FakeMessage:
    def __init__(self, values: dict):
        self._values = values

    def get_value(self, name: str):
        return self._values.get(name)


def _fake_fit_file(session_values: dict, record_values: list[dict]) -> MagicMock:
    fake = MagicMock()

    def get_messages(name: str):
        if name == "session":
            return [_FakeMessage(session_values)] if session_values else []
        if name == "record":
            return [_FakeMessage(v) for v in record_values]
        raise AssertionError(f"unexpected message type requested in test: {name}")

    fake.get_messages.side_effect = get_messages
    return fake


def test_parses_valid_activity_into_points_and_metadata() -> None:
    started_at = datetime(2026, 8, 15, 14, 30, tzinfo=UTC)
    # position values are in "semicircles"; 100_000_000 semicircles ~= 8.38 degrees.
    fake_fit = _fake_fit_file(
        session_values={"sport": "golf", "start_time": started_at},
        record_values=[
            {"position_lat": 401_000_000, "position_long": -871_000_000, "timestamp": started_at},
            {"position_lat": 401_000_500, "position_long": -871_000_400, "timestamp": started_at},
            {"position_lat": None, "position_long": None, "timestamp": started_at},  # no GPS fix
        ],
    )

    with patch("app.services.parsers.fit_parser.FitFile", return_value=fake_fit):
        result = parse_fit_activity(b"irrelevant-because-FitFile-is-mocked")

    assert result.status == RoundStatus.needs_audit
    assert result.sport == "golf"
    assert result.started_at == started_at
    assert len(result.points) == 2  # the point missing lat/long is skipped
    assert result.points[0] == GpsPoint(
        latitude=401_000_000 * (180 / 2**31),
        longitude=-871_000_000 * (180 / 2**31),
        timestamp=started_at,
    )


def test_too_few_gps_points_flags_casual_practice() -> None:
    fake_fit = _fake_fit_file(
        session_values={"sport": "golf", "start_time": None},
        record_values=[
            {"position_lat": 401_000_000, "position_long": -871_000_000, "timestamp": None}
        ],
    )

    with patch("app.services.parsers.fit_parser.FitFile", return_value=fake_fit):
        result = parse_fit_activity(b"irrelevant")

    assert result.status == RoundStatus.casual_practice
    assert len(result.points) == 1


def test_corrupted_fit_file_flags_casual_practice_instead_of_raising() -> None:
    result = parse_fit_activity(str(FIXTURES_DIR / "corrupted.fit"))

    assert result.status == RoundStatus.casual_practice
    assert result.points == []
    assert result.sport is None


def test_empty_bytes_flags_casual_practice_instead_of_raising() -> None:
    result = parse_fit_activity(b"")

    assert result.status == RoundStatus.casual_practice
    assert result.points == []
