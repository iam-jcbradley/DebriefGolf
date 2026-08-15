"""Unit tests for garmin_client.py's own logic (login flow, MFA handling,
error wrapping, FIT extraction), mocking the underlying `garminconnect.Garmin`
object throughout. This is the same boundary every other unverifiable-live
integration in this repo uses: real, tested code around the parts we
control, without a live Garmin account to round-trip against (see the
module docstring in garmin_client.py).
"""

import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from garmin_client import GarminImportClient, GarminImportError, MfaRequiredError


def _client_with_mock_garmin() -> tuple[GarminImportClient, MagicMock]:
    with patch("garmin_client.Garmin") as mock_garmin_cls:
        mock_garmin = MagicMock()
        mock_garmin_cls.return_value = mock_garmin
        client = GarminImportClient("test@example.com", "password", "/tmp/test_tokenstore")
    return client, mock_garmin


class TestLogin:
    def test_successful_login_sets_logged_in(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        mock_garmin.login.return_value = (None, None)

        client.login()

        assert client._logged_in is True
        mock_garmin.login.assert_called_once_with(tokenstore="/tmp/test_tokenstore")

    def test_mfa_required_raises_without_setting_logged_in(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        mock_garmin.login.return_value = ("needs_mfa", None)

        with pytest.raises(MfaRequiredError):
            client.login()

        assert client._logged_in is False

    def test_authentication_error_wrapped(self) -> None:
        from garminconnect import GarminConnectAuthenticationError

        client, mock_garmin = _client_with_mock_garmin()
        mock_garmin.login.side_effect = GarminConnectAuthenticationError("bad creds")

        with pytest.raises(GarminImportError, match="Authentication failed"):
            client.login()

    def test_connection_error_wrapped(self) -> None:
        from garminconnect import GarminConnectConnectionError

        client, mock_garmin = _client_with_mock_garmin()
        mock_garmin.login.side_effect = GarminConnectConnectionError("network down")

        with pytest.raises(GarminImportError, match="Could not reach Garmin"):
            client.login()

    def test_rate_limit_error_wrapped(self) -> None:
        from garminconnect import GarminConnectTooManyRequestsError

        client, mock_garmin = _client_with_mock_garmin()
        mock_garmin.login.side_effect = GarminConnectTooManyRequestsError("slow down")

        with pytest.raises(GarminImportError, match="Rate limited"):
            client.login()


class TestResumeMfa:
    def test_completes_login_and_persists_tokens(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()

        client.resume_mfa("123456")

        mock_garmin.resume_login.assert_called_once_with({}, "123456")
        mock_garmin.client.dump.assert_called_once_with("/tmp/test_tokenstore")
        assert client._logged_in is True


class TestRequireLogin:
    def test_methods_raise_before_login(self) -> None:
        client, _ = _client_with_mock_garmin()

        with pytest.raises(GarminImportError, match="Not logged in"):
            client.list_scorecards()
        with pytest.raises(GarminImportError, match="Not logged in"):
            client.get_scorecard("1")
        with pytest.raises(GarminImportError, match="Not logged in"):
            client.get_shot_data("1")
        with pytest.raises(GarminImportError, match="Not logged in"):
            client.list_golf_activities()
        with pytest.raises(GarminImportError, match="Not logged in"):
            client.download_fit("1", "/tmp")


class TestGolfMethods:
    def test_list_scorecards_calls_get_golf_summary(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True
        mock_garmin.get_golf_summary.return_value = [{"scorecardId": 1}]

        result = client.list_scorecards(limit=5)

        mock_garmin.get_golf_summary.assert_called_once_with(start=0, limit=5)
        assert result == [{"scorecardId": 1}]

    def test_get_scorecard_calls_get_golf_scorecard(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True
        mock_garmin.get_golf_scorecard.return_value = {"scorecardId": 42}

        result = client.get_scorecard("42")

        mock_garmin.get_golf_scorecard.assert_called_once_with("42")
        assert result == {"scorecardId": 42}

    def test_get_shot_data_omits_hole_numbers_when_not_given(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True
        mock_garmin.get_golf_shot_data.return_value = {}

        client.get_shot_data("42")

        mock_garmin.get_golf_shot_data.assert_called_once_with("42")

    def test_get_shot_data_passes_hole_numbers_when_given(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True
        mock_garmin.get_golf_shot_data.return_value = {}

        client.get_shot_data("42", hole_numbers="1,2,3")

        mock_garmin.get_golf_shot_data.assert_called_once_with("42", hole_numbers="1,2,3")

    def test_list_golf_activities_handles_list_response(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True
        mock_garmin.get_activities.return_value = [{"activityId": 1}]

        result = client.list_golf_activities()

        assert result == [{"activityId": 1}]

    def test_list_golf_activities_handles_dict_response(self) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True
        mock_garmin.get_activities.return_value = {"activities": [{"activityId": 1}]}

        result = client.list_golf_activities()

        assert result == [{"activityId": 1}]


class TestDownloadFit:
    def test_extracts_fit_file_from_zip(self, tmp_path) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("12345.fit", b"fake fit bytes")
        mock_garmin.download_activity.return_value = buf.getvalue()

        out_path = client.download_fit("12345", tmp_path)

        assert out_path == tmp_path / "12345.fit"
        assert out_path.read_bytes() == b"fake fit bytes"

    def test_raises_when_zip_has_no_fit_file(self, tmp_path) -> None:
        client, mock_garmin = _client_with_mock_garmin()
        client._logged_in = True

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", b"no fit here")
        mock_garmin.download_activity.return_value = buf.getvalue()

        with pytest.raises(GarminImportError, match="no .FIT file"):
            client.download_fit("12345", tmp_path)


class TestTokenStatus:
    def test_reports_tokenstore_existence_and_login_state(self, tmp_path) -> None:
        tokenstore = tmp_path / "tokens"
        with patch("garmin_client.Garmin"):
            client = GarminImportClient("test@example.com", "password", tokenstore)

        status = client.token_status()
        assert status["tokenstore_exists"] is False
        assert status["logged_in"] is False

        tokenstore.mkdir()
        status = client.token_status()
        assert status["tokenstore_exists"] is True
