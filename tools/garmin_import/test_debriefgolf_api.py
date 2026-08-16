"""Tests for debriefgolf_api.py, mocking the underlying `requests.Session`
so no real DebriefGolf API needs to be running."""

from unittest.mock import MagicMock, patch

import pytest

from debriefgolf_api import DebriefGolfApiError, DebriefGolfClient


def _client_with_mock_session() -> tuple[DebriefGolfClient, MagicMock]:
    with patch("debriefgolf_api.requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        client = DebriefGolfClient("http://localhost:8000")
    return client, mock_session


def _ok_response(json_body):
    response = MagicMock()
    response.ok = True
    response.json.return_value = json_body
    return response


def _error_response(status_code: int, text: str):
    response = MagicMock()
    response.ok = False
    response.status_code = status_code
    response.text = text
    return response


class TestLogin:
    def test_posts_credentials(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _ok_response({"id": 1})

        client.login("golfer@example.com", "hunter2")

        mock_session.post.assert_called_once_with(
            "http://localhost:8000/api/auth/login",
            json={"email": "golfer@example.com", "password": "hunter2"},
            timeout=30,
        )

    def test_raises_on_failure(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _error_response(401, "Incorrect email or password")

        with pytest.raises(DebriefGolfApiError, match="Login failed"):
            client.login("golfer@example.com", "wrong")


class TestFindCourseByName:
    def test_returns_case_insensitive_exact_match(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.get.return_value = _ok_response(
            [{"id": 1, "name": "fake golf course"}, {"id": 2, "name": "Other Course"}]
        )

        result = client.find_course_by_name("Fake Golf Course")

        assert result == {"id": 1, "name": "fake golf course"}

    def test_returns_none_when_no_exact_match(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.get.return_value = _ok_response([{"id": 2, "name": "Other Course"}])

        assert client.find_course_by_name("Fake Golf Course") is None

    def test_raises_on_failure(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.get.return_value = _error_response(401, "Not authenticated")

        with pytest.raises(DebriefGolfApiError, match="Course lookup failed"):
            client.find_course_by_name("Fake Golf Course")


class TestCreateCourse:
    def test_returns_created_course(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _ok_response({"id": 3, "name": "New Course"})

        result = client.create_course({"name": "New Course", "holes": []})

        assert result == {"id": 3, "name": "New Course"}

    def test_raises_on_failure(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _error_response(422, "Hole numbers must be unique")

        with pytest.raises(DebriefGolfApiError, match="Course creation failed"):
            client.create_course({"name": "New Course", "holes": []})


class TestCreateRound:
    def test_returns_created_round(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _ok_response({"id": 9, "status": "needs_audit"})

        result = client.create_round({"course_id": 3})

        assert result == {"id": 9, "status": "needs_audit"}

    def test_raises_on_failure(self) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _error_response(404, "Course not found")

        with pytest.raises(DebriefGolfApiError, match="Round creation failed"):
            client.create_round({"course_id": 999})


class TestUploadFit:
    def test_uploads_file_contents(self, tmp_path) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _ok_response({"round_id": 5})
        fit_path = tmp_path / "activity.fit"
        fit_path.write_bytes(b"fake fit bytes")

        result = client.upload_fit(fit_path)

        assert result == {"round_id": 5}
        _, kwargs = mock_session.post.call_args
        assert kwargs["files"]["file"][0] == "activity.fit"

    def test_raises_on_failure(self, tmp_path) -> None:
        client, mock_session = _client_with_mock_session()
        mock_session.post.return_value = _error_response(401, "Not authenticated")
        fit_path = tmp_path / "activity.fit"
        fit_path.write_bytes(b"fake fit bytes")

        with pytest.raises(DebriefGolfApiError, match="Upload failed"):
            client.upload_fit(fit_path)
