"""Thin client for DebriefGolf's own API, used to push imported Garmin data
in. Since Phase 10, every DebriefGolf endpoint that touches user data reads
identity from a signed session cookie (`app/api/deps.py`) and accepts no
`user_id` parameter at all — so this client logs in with a real DebriefGolf
account (`POST /api/auth/login`) through a `requests.Session`, which keeps
the cookie for every subsequent call automatically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests


class DebriefGolfApiError(Exception):
    pass


class DebriefGolfClient:
    def __init__(self, api_url: str) -> None:
        self.api_url = api_url.rstrip("/")
        self._session = requests.Session()

    def login(self, email: str, password: str) -> None:
        response = self._session.post(
            f"{self.api_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        if not response.ok:
            raise DebriefGolfApiError(f"Login failed ({response.status_code}): {response.text}")

    def find_course_by_name(self, name: str) -> dict[str, Any] | None:
        """Exact (case-insensitive) name match among `GET /courses?q=name`
        results. DebriefGolf only de-duplicates courses by `osm_relation_id`
        server-side (`POST /courses`), and a Garmin scorecard course has
        none — so this is this tool's own idempotency check, to avoid
        creating a duplicate course every time the same course is imported.
        """
        response = self._session.get(
            f"{self.api_url}/api/courses", params={"q": name}, timeout=30
        )
        if not response.ok:
            raise DebriefGolfApiError(
                f"Course lookup failed ({response.status_code}): {response.text}"
            )
        for course in response.json():
            if course["name"].strip().lower() == name.strip().lower():
                return course
        return None

    def create_course(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._session.post(f"{self.api_url}/api/courses", json=payload, timeout=30)
        if not response.ok:
            raise DebriefGolfApiError(
                f"Course creation failed ({response.status_code}): {response.text}"
            )
        return response.json()

    def create_round(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._session.post(f"{self.api_url}/api/rounds", json=payload, timeout=30)
        if not response.ok:
            raise DebriefGolfApiError(
                f"Round creation failed ({response.status_code}): {response.text}"
            )
        return response.json()

    def upload_fit(self, fit_path: str | Path) -> dict[str, Any]:
        fit_path = Path(fit_path)
        with fit_path.open("rb") as f:
            response = self._session.post(
                f"{self.api_url}/api/rounds/upload",
                files={"file": (fit_path.name, f)},
                timeout=30,
            )
        if not response.ok:
            raise DebriefGolfApiError(f"Upload failed ({response.status_code}): {response.text}")
        return response.json()
