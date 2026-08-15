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
    python main.py upload FIT_PATH --user-id N [--api-url URL]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from garmin_client import GarminImportClient, GarminImportError, MfaRequiredError

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
    print(f"Upload it to DebriefGolf with: python main.py upload {fit_path} --user-id <N>")


def cmd_upload(args: argparse.Namespace) -> None:
    fit_path = Path(args.fit_path)
    if not fit_path.exists():
        print(f"File not found: {fit_path}", file=sys.stderr)
        sys.exit(1)

    url = f"{args.api_url.rstrip('/')}/api/rounds/upload?user_id={args.user_id}"
    with fit_path.open("rb") as f:
        response = requests.post(url, files={"file": (fit_path.name, f)}, timeout=30)

    if not response.ok:
        print(f"Upload failed ({response.status_code}): {response.text}", file=sys.stderr)
        sys.exit(1)

    print(f"Uploaded — {response.json()}")


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
    upload_parser.add_argument("--user-id", type=int, required=True)
    upload_parser.add_argument("--api-url", default=DEFAULT_API_URL)
    upload_parser.set_defaults(func=cmd_upload)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
