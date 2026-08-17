"""Outbound email (Phase 15). No real SMTP server is reachable from this
sandbox — see app/services/email.py's docstring — so every test here mocks
the transport rather than exercising a live one."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.email import EmailError, send_email


@pytest.fixture(autouse=True)
def _reset_smtp_settings(monkeypatch):
    """Every test starts from the same known settings rather than whatever
    an earlier test (or a developer's real .env) left behind."""
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_from", "Debrief Golf <no-reply@debriefgolf.app>")
    monkeypatch.setattr(settings, "smtp_use_tls", True)


def test_logs_instead_of_sending_when_no_smtp_host_configured(caplog) -> None:
    with caplog.at_level("INFO", logger="app.email"):
        send_email(to="jane@example.com", subject="Reset your password", body="link here")

    assert "jane@example.com" in caplog.text
    assert "Reset your password" in caplog.text
    assert "link here" in caplog.text


def test_dev_mode_never_touches_smtplib() -> None:
    with patch("smtplib.SMTP") as mock_smtp:
        send_email(to="jane@example.com", subject="Subject", body="Body")
    mock_smtp.assert_not_called()


def test_sends_over_smtp_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_username", "apikey")
    monkeypatch.setattr(settings, "smtp_password", "secret")

    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    with patch("smtplib.SMTP", return_value=mock_conn) as mock_smtp:
        send_email(to="jane@example.com", subject="Reset your password", body="link here")

    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_conn.starttls.assert_called_once()
    mock_conn.login.assert_called_once_with("apikey", "secret")
    mock_conn.send_message.assert_called_once()

    sent_message = mock_conn.send_message.call_args[0][0]
    assert sent_message["To"] == "jane@example.com"
    assert sent_message["Subject"] == "Reset your password"
    assert sent_message.get_content().strip() == "link here"


def test_skips_login_without_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    # smtp_username stays "" from the autouse fixture.

    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    with patch("smtplib.SMTP", return_value=mock_conn):
        send_email(to="jane@example.com", subject="Subject", body="Body")

    mock_conn.login.assert_not_called()


def test_skips_starttls_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_use_tls", False)

    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    with patch("smtplib.SMTP", return_value=mock_conn):
        send_email(to="jane@example.com", subject="Subject", body="Body")

    mock_conn.starttls.assert_not_called()


def test_raises_email_error_on_smtp_failure(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")

    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.send_message.side_effect = smtplib.SMTPException("mailbox full")
    with patch("smtplib.SMTP", return_value=mock_conn):
        with pytest.raises(EmailError, match="mailbox full"):
            send_email(to="jane@example.com", subject="Subject", body="Body")


def test_raises_email_error_on_connection_failure(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")

    with patch("smtplib.SMTP", side_effect=OSError("connection refused")):
        with pytest.raises(EmailError, match="connection refused"):
            send_email(to="jane@example.com", subject="Subject", body="Body")
