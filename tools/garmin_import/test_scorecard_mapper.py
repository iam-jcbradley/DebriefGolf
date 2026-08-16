"""Tests for scorecard_mapper.py, fixtured against a real (sanitized) Garmin
`.../scorecard/detail` response — see garmin_client.py's module docstring
for provenance. `SANITIZED_DETAIL` is exactly the shape
`GarminImportClient.get_scorecard` should return for one scorecard: a
`scorecardDetails` array with one `{scorecard, scorecardStats}` entry, and a
`courseSnapshots` array with one course.
"""

import copy

import pytest

from scorecard_mapper import (
    ScorecardMappingError,
    map_course_payload,
    map_round_payload,
)

SANITIZED_DETAIL = {
    "scorecardDetails": [
        {
            "scorecard": {
                "id": 99999992,
                "startTime": "2021-03-18T01:57:28.000Z",
                "formattedStartTime": "2021-03-17T20:57:28-05:00",
                "endTime": "2021-03-18T01:57:41.000Z",
                "scoreType": "STROKE_PLAY",
                "teeBox": "Blue",
                "handicapType": "MEN",
                "teeBoxRating": 70,
                "teeBoxSlope": 124,
                "handicappedStrokes": 12,
                "strokes": 12,
                "holesCompleted": 2,
                "holes": [
                    {"number": 1, "strokes": 5, "handicapScore": 5},
                    {"number": 2, "pinPositionLat": 1, "pinPositionLon": -1},
                ],
            },
            "scorecardStats": {
                "frontNine": {"holesPlayed": 2, "fairwaysHit": 0, "putts": 0, "strokes": 12},
                "backNine": {"holesPlayed": 0, "fairwaysHit": 0, "putts": 0, "strokes": 0},
                "round": {"holesPlayed": 2, "fairwaysHit": 0, "putts": 0, "strokes": 12},
            },
        }
    ],
    "courseSnapshots": [
        {
            "courseGlobalId": 156781234,
            "courseSnapshotId": 43249999,
            "name": "Fake Golf Course",
            "holePars": "445435354445343444",
            "country": "Canada",
            "city": "Toronto",
            "state": "ON",
            "frontNinePar": 37,
            "backNinePar": 35,
            "roundPar": 72,
            "tees": [
                {"name": "Blue", "handicapType": "MEN", "rating": 70, "slope": 124},
            ],
        }
    ],
}


class TestMapCoursePayload:
    def test_maps_name_city_state(self) -> None:
        payload = map_course_payload(SANITIZED_DETAIL)
        assert payload["name"] == "Fake Golf Course"
        assert payload["city"] == "Toronto"
        assert payload["state"] == "ON"

    def test_maps_one_hole_per_par_digit_with_unknown_yardage(self) -> None:
        payload = map_course_payload(SANITIZED_DETAIL)
        assert len(payload["holes"]) == 18
        assert payload["holes"][0] == {"number": 1, "par": 4, "yardage": 0}
        assert payload["holes"][17] == {"number": 18, "par": 4, "yardage": 0}
        # Sum of parsed pars matches Garmin's own reported roundPar.
        assert sum(h["par"] for h in payload["holes"]) == 72

    def test_raises_when_no_course_snapshot(self) -> None:
        detail = copy.deepcopy(SANITIZED_DETAIL)
        detail["courseSnapshots"] = []
        with pytest.raises(ScorecardMappingError, match="courseSnapshots"):
            map_course_payload(detail)

    def test_raises_when_two_course_snapshots(self) -> None:
        detail = copy.deepcopy(SANITIZED_DETAIL)
        detail["courseSnapshots"] = detail["courseSnapshots"] * 2
        with pytest.raises(ScorecardMappingError, match="courseSnapshots"):
            map_course_payload(detail)

    def test_raises_when_hole_pars_missing(self) -> None:
        detail = copy.deepcopy(SANITIZED_DETAIL)
        del detail["courseSnapshots"][0]["holePars"]
        with pytest.raises(ScorecardMappingError, match="holePars"):
            map_course_payload(detail)


class TestMapRoundPayload:
    def test_maps_played_at_and_score(self) -> None:
        payload = map_round_payload(SANITIZED_DETAIL, course_id=7)
        assert payload["course_id"] == 7
        assert payload["played_at"] == "2021-03-18T01:57:28.000Z"
        assert payload["total_score"] == 12
        assert payload["status"] == "needs_audit"

    def test_raises_when_no_scorecard_entry(self) -> None:
        detail = copy.deepcopy(SANITIZED_DETAIL)
        detail["scorecardDetails"] = []
        with pytest.raises(ScorecardMappingError, match="scorecardDetails"):
            map_round_payload(detail, course_id=1)

    def test_raises_when_start_time_missing(self) -> None:
        detail = copy.deepcopy(SANITIZED_DETAIL)
        del detail["scorecardDetails"][0]["scorecard"]["startTime"]
        with pytest.raises(ScorecardMappingError, match="startTime"):
            map_round_payload(detail, course_id=1)
