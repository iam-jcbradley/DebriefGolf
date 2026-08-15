from pathlib import Path

from app.services.parsers.launch_monitor_parser import (
    parse_launch_monitor_csv,
    parse_launch_monitor_json,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_parses_valid_csv_fixture() -> None:
    result = parse_launch_monitor_csv((FIXTURES_DIR / "launch_monitor.csv").read_text())

    assert result.errors == []
    assert [s.club for s in result.shots] == ["Driver", "7-Iron", "PW"]

    driver = result.shots[0]
    assert driver.club_speed_mph == 104.2
    assert driver.ball_speed_mph == 152.1
    assert driver.smash_factor == 1.46
    assert driver.spin_axis_deg == -3.1
    assert driver.carry_yards == 251.3
    assert driver.total_yards == 268.9
    assert driver.captured_at is not None and driver.captured_at.hour == 9


def test_derives_smash_factor_when_missing_from_speeds() -> None:
    csv_text = (
        "Club,Club Speed,Ball Speed,Carry\n"
        "7-Iron,80.0,108.0,155\n"
    )
    result = parse_launch_monitor_csv(csv_text)

    assert result.errors == []
    assert result.shots[0].smash_factor == 1.35


def test_tolerant_of_header_case_and_punctuation_variants() -> None:
    csv_text = (
        "CLUB, club-speed (MPH) , ball_speed_mph, carry yds\n"
        "Driver,100,140,240\n"
    )
    result = parse_launch_monitor_csv(csv_text)

    assert result.errors == []
    shot = result.shots[0]
    assert shot.club == "Driver"
    assert shot.club_speed_mph == 100.0
    assert shot.ball_speed_mph == 140.0
    assert shot.carry_yards == 240.0


def test_missing_tokens_parsed_as_none_not_error() -> None:
    csv_text = "Club,Carry,Total,Spin Axis\nPutter,--,5,N/A\n"
    result = parse_launch_monitor_csv(csv_text)

    assert result.errors == []
    assert result.shots[0].carry_yards is None
    assert result.shots[0].total_yards == 5.0
    assert result.shots[0].spin_axis_deg is None


def test_malformed_rows_are_skipped_with_errors_not_raised() -> None:
    csv_text = (
        "Club,Carry,Total\n"
        "Driver,250,270\n"
        ",240,260\n"  # missing club -> row error
        "7-Iron,,\n"  # missing both carry and total -> row error
        "PW,120,125\n"
    )
    result = parse_launch_monitor_csv(csv_text)

    assert [s.club for s in result.shots] == ["Driver", "PW"]
    assert len(result.errors) == 2
    assert "row 3" in result.errors[0]
    assert "row 4" in result.errors[1]


def test_csv_with_no_header_row_reports_error() -> None:
    result = parse_launch_monitor_csv("")
    assert result.shots == []
    assert result.errors == ["CSV has no header row"]


def test_parses_valid_json_fixture() -> None:
    result = parse_launch_monitor_json((FIXTURES_DIR / "launch_monitor.json").read_text())

    assert result.errors == []
    assert [s.club for s in result.shots] == ["Driver", "6-Iron"]
    driver = result.shots[0]
    assert driver.carry_yards == 254.1
    assert driver.smash_factor == 1.46
    # second shot has smash_factor: null in the fixture -> derived from speeds.
    six_iron = result.shots[1]
    assert six_iron.smash_factor == round(119.7 / 88.3, 3)


def test_json_bare_array_supported() -> None:
    result = parse_launch_monitor_json('[{"club": "SW", "carry": 90}]')
    assert result.errors == []
    assert result.shots[0].club == "SW"


def test_invalid_json_reports_error_not_raise() -> None:
    result = parse_launch_monitor_json("{not valid json")
    assert result.shots == []
    assert "invalid JSON" in result.errors[0]


def test_json_non_object_records_reported_as_errors() -> None:
    result = parse_launch_monitor_json('[{"club": "Driver", "carry": 250}, "oops"]')
    assert len(result.shots) == 1
    assert "record 2" in result.errors[0]
