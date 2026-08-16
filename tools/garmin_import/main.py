#!/usr/bin/env python3
"""CLI for tools/garmin_import — see garmin_client.py's module docstring
for the auth mechanics and honest caveats (ToS, fragility, unverified
golf-JSON schema). Everything here runs on your own machine; your Garmin
credentials never reach the DebriefGolf backend.

Usage:
    python main.py status
    python main.py list [--limit N]
    python main.py export SCORECARD_ID
    python main.py shots SCORECARD_ID [--holes 1,2,3]
    python main.py download-fit ACTIVITY_ID
    python main.py upload FIT_PATH [--api-url URL]
    python main.py import-scorecard SCORECARD_ID [--api-url URL]

`upload` and `import-scorecard` authenticate against DebriefGolf's own API
with a real account (DEBRIEFGOLF_EMAIL / DEBRIEFGOLF_PASSWORD in .env) —
identity there comes from a signed session cookie, not a user-id parameter.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from debriefgolf_api import DebriefGolfApiError, DebriefGolfClient
from garmin_client import GarminImportClient, GarminImportError, MfaRequiredError
from scorecard_mapper import ScorecardMappingError, map_course_payload, map_round_payload

DEFAULT_TOKENSTORE = Path(__file__).parent / ".garmin_tokens"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_API_URL = "http://localhost:8000"


def _build_client() -> GarminImportClient:
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        print(
            "GARMIN_EMAIL / GARMIN_PASSWORD not set — copy .env.example to .env "
            "and fill them in.",
            file=sys.stderr,
        )
        sys.exit(1)
    DEFAULT_TOKENSTORE.mkdir(parents=True, exist_ok=True)
    return GarminImportClient(email, password, DEFAULT_TOKENSTORE)


def _build_debriefgolf_client(api_url: str) -> DebriefGolfClient:
    email = os.getenv("DEBRIEFGOLF_EMAIL")
    password = os.getenv("DEBRIEFGOLF_PASSWORD")
    if not email or not password:
        print(
            "DEBRIEFGOLF_EMAIL / DEBRIEFGOLF_PASSWORD not set — copy .env.example to .env "
            "and fill them in with a real DebriefGolf account (identity comes from a "
            "session cookie now, not a user-id parameter).",
            file=sys.stderr,
        )
        sys.exit(1)
    client = DebriefGolfClient(api_url)
    try:
        client.login(email, password)
    except DebriefGolfApiError as exc:
        print(f"DebriefGolf login failed: {exc}", file=sys.stderr)
        sys.exit(1)
    return client


def _login_with_mfa_prompt(client: GarminImportClient) -> None:
    try:
        client.login()
    except MfaRequiredError:
        print("Garmin is asking for a 2FA/MFA code (check your authenticator app or email).")
        code = input("Enter the code: ").strip()
        try:
            client.resume_mfa(code)
        except GarminImportError as exc:
            print(f"MFA failed: {exc}", file=sys.stderr)
            sys.exit(1)
    except GarminImportError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_status(_args: argparse.Namespace) -> None:
    client = _build_client()
    before = client.token_status()
    print(f"Tokenstore: {before['tokenstore']} (exists: {before['tokenstore_exists']})")
    _login_with_mfa_prompt(client)
    after = client.token_status()
    print(f"Logged in as: {after['display_name'] or '(name unavailable)'}")


def cmd_list(args: argparse.Namespace) -> None:
    client = _build_client()
    _login_with_mfa_prompt(client)
    try:
        scorecards = client.list_scorecards(limit=args.limit)
    except GarminImportError as exc:
        print(f"Failed to list scorecards: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(scorecards, indent=2, default=str))


def cmd_export(args: argparse.Namespace) -> None:
    client = _build_client()
    _login_with_mfa_prompt(client)
    try:
        detail = client.get_scorecard(args.scorecard_id)
    except GarminImportError as exc:
        print(f"Failed to fetch scorecard {args.scorecard_id}: {exc}", file=sys.stderr)
        sys.exit(1)

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DEFAULT_OUTPUT_DIR / f"scorecard_{args.scorecard_id}.json"
    out_path.write_text(json.dumps(detail, indent=2, default=str))
    print(f"Saved {out_path}")


def cmd_shots(args: argparse.Namespace) -> None:
    client = _build_client()
    _login_with_mfa_prompt(client)
    try:
        shots = client.get_shot_data(args.scorecard_id, hole_numbers=args.holes)
    except GarminImportError as exc:
        print(f"Failed to fetch shot data for {args.scorecard_id}: {exc}", file=sys.stderr)
        sys.exit(1)

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DEFAULT_OUTPUT_DIR / f"shots_{args.scorecard_id}.json"
    out_path.write_text(json.dumps(shots, indent=2, default=str))
    print(f"Saved {out_path}")


def cmd_download_fit(args: argparse.Namespace) -> None:
    client = _build_client()
    _login_with_mfa_prompt(client)
    try:
        fit_path = client.download_fit(args.activity_id, DEFAULT_OUTPUT_DIR)
    except GarminImportError as exc:
        print(f"Failed to download activity {args.activity_id}: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Saved {fit_path}")
    print(f"Upload it to DebriefGolf with: python main.py upload {fit_path}")


def cmd_upload(args: argparse.Namespace) -> None:
    fit_path = Path(args.fit_path)
    if not fit_path.exists():
        print(f"File not found: {fit_path}", file=sys.stderr)
        sys.exit(1)

    client = _build_debriefgolf_client(args.api_url)
    try:
        result = client.upload_fit(fit_path)
    except DebriefGolfApiError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(f"Uploaded — {result}")


def cmd_import_scorecard(args: argparse.Namespace) -> None:
    garmin = _build_client()
    _login_with_mfa_prompt(garmin)
    try:
        detail = garmin.get_scorecard(args.scorecard_id)
    except GarminImportError as exc:
        print(f"Failed to fetch scorecard {args.scorecard_id}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        course_payload = map_course_payload(detail)
        # course_id filled in below, once we know it — everything else in the
        # round payload is mappable now, so validate it before touching the
        # API rather than risk creating a course and then failing.
        round_payload = map_round_payload(detail, course_id=None)
    except ScorecardMappingError as exc:
        print(f"Could not map scorecard {args.scorecard_id}: {exc}", file=sys.stderr)
        sys.exit(1)

    debrief = _build_debriefgolf_client(args.api_url)
    try:
        existing = debrief.find_course_by_name(course_payload["name"])
        if existing:
            course = existing
            print(f"Reusing existing course: {course['name']} (id={course['id']})")
        else:
            course = debrief.create_course(course_payload)
            print(f"Created course: {course['name']} (id={course['id']})")
            print(
                "  Hole yardages are unknown (Garmin's scorecard JSON doesn't include "
                "them) — set to 0. Fill them in via the course editor."
            )

        round_payload["course_id"] = course["id"]
        round_ = debrief.create_round(round_payload)
        print(f"Created round: id={round_['id']}, status={round_['status']}")
        print(
            "  No shots attached — status is 'needs_audit'. Pair with an uploaded .FIT "
            "for the same round (see 'download-fit' + 'upload') to get shot-level data."
        )
    except DebriefGolfApiError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def main() -> None:
    load_dotenv(Path(__file__).parent / ".env")

    parser = argparse.ArgumentParser(description="Export Garmin golf data into DebriefGolf")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Test login / show token status")
    status_parser.set_defaults(func=cmd_status)

    list_parser = subparsers.add_parser("list", help="List recent golf scorecards")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.set_defaults(func=cmd_list)

    export_parser = subparsers.add_parser("export", help="Export a scorecard's detail to JSON")
    export_parser.add_argument("scorecard_id")
    export_parser.set_defaults(func=cmd_export)

    shots_parser = subparsers.add_parser(
        "shots", help="Export a scorecard's shot-by-shot data to JSON"
    )
    shots_parser.add_argument("scorecard_id")
    shots_parser.add_argument(
        "--holes", default=None, help="Comma-separated hole numbers, e.g. 1,2,3"
    )
    shots_parser.set_defaults(func=cmd_shots)

    fit_parser = subparsers.add_parser("download-fit", help="Download an activity's raw .FIT file")
    fit_parser.add_argument("activity_id")
    fit_parser.set_defaults(func=cmd_download_fit)

    upload_parser = subparsers.add_parser(
        "upload", help="Upload a downloaded .FIT file to a running DebriefGolf API"
    )
    upload_parser.add_argument("fit_path")
    upload_parser.add_argument("--api-url", default=DEFAULT_API_URL)
    upload_parser.set_defaults(func=cmd_upload)

    import_parser = subparsers.add_parser(
        "import-scorecard",
        help="Import a scorecard's score/course metadata into DebriefGolf (no shots)",
    )
    import_parser.add_argument("scorecard_id")
    import_parser.add_argument("--api-url", default=DEFAULT_API_URL)
    import_parser.set_defaults(func=cmd_import_scorecard)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
