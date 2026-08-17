"""Outbound email (Phase 15).

Password reset is the only caller today. There is no SMTP server reachable
from this sandbox, so `send_email` logs the message instead of transmitting
it whenever `settings.smtp_host` is blank — the same unverifiable-boundary
convention as `garmin_oauth.py` and `osm_courses.py`: standards-conformant
code, unit-tested against a mocked transport, verification limit stated
plainly here rather than pretended away.

A real deployment sets `SMTP_*` in settings and gets a real send over
`smtplib` — the stdlib is enough for one transactional email use case, no
provider SDK needed.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("app.email")


class EmailError(Exception):
    """The message was addressed to send, but the SMTP transport rejected
    or failed to deliver it. Never raised for the dev no-SMTP-configured
    path — that's the expected local mode, not a failure."""


def send_email(*, to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.info("EMAIL (dev, not sent) to=%s subject=%r\n%s", to, subject, body)
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailError(f"Failed to send email to {to}: {exc}") from exc
