"""Times the hot endpoints against a realistically-sized dataset.

Every query in this app was written against a demo database holding one
round. This seeds hundreds of rounds and tens of thousands of shots into a
throwaway `<database>_bench` database and times the endpoints the dashboard,
Smart Bag and Practice Hub actually call, so "this won't scale" can be a
measurement rather than an opinion.

    uv run python scripts/benchmark.py            # default 300 rounds
    uv run python scripts/benchmark.py --rounds 800

A second user is always seeded with the same volume, so any endpoint that
accidentally stopped scoping to the caller shows up as both wrong *and*
slow.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import URL, Engine, create_engine, make_url, text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.api.deps import get_current_user  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Course,
    Hole,
    Lie,
    PracticeSession,
    PracticeShot,
    Round,
    RoundStatus,
    Shot,
    User,
)

API_ROOT = Path(__file__).resolve().parent.parent
CLUBS = ["Driver", "3-Wood", "5-Iron", "7-Iron", "9-Iron", "PW", "SW", "Putter"]
HOLE_LAYOUT = [(4, 400), (4, 385), (3, 175), (5, 540), (4, 410), (3, 160), (4, 418),
               (5, 525), (4, 395), (4, 405), (3, 190), (5, 555), (4, 375), (4, 410),
               (3, 170), (4, 440), (5, 510), (4, 430)]


def _bench_database_url() -> URL:
    configured = make_url(settings.database_url)
    return configured.set(database=f"{configured.database}_bench")


def _provision(url: URL) -> Engine:
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["sqlalchemy_url"] = url.render_as_string(hide_password=False)
    command.upgrade(config, "head")
    return engine


def _wipe(engine: Engine) -> None:
    with engine.begin() as connection:
        for table in ("shot", "round", "practice_shot", "practice_session",
                      "virtual_round", "garmin_connection", "hole", "course", '"user"'):
            connection.execute(text(f"DELETE FROM {table}"))


def _seed_user(session: Session, email: str, course_id: int, hole_ids: list[int],
               rounds: int, rng: random.Random) -> User:
    user = User(email=email, name=email.split("@")[0], handicap_index=10.0)
    session.add(user)
    session.commit()
    session.refresh(user)

    round_rows = [
        {"user_id": user.id, "course_id": course_id, "total_score": 78 + rng.randint(-4, 8),
         "status": RoundStatus.verified, "played_at": time.strftime("%Y-%m-%d")}
        for _ in range(rounds)
    ]
    session.execute(Round.__table__.insert(), round_rows)
    session.commit()

    round_ids = list(session.exec(select(Round.id).where(Round.user_id == user.id)).all())

    shot_rows = []
    for round_id in round_ids:
        for hole_index, hole_id in enumerate(hole_ids):
            par = HOLE_LAYOUT[hole_index][0]
            for shot_number in range(1, par + 1):
                putt = shot_number > par - 2
                holed = shot_number == par
                shot_rows.append({
                    "round_id": round_id,
                    "hole_id": hole_id,
                    "shot_number": shot_number,
                    "club": "Putter" if putt else rng.choice(CLUBS[:-1]),
                    "start_lie": Lie.green if putt else Lie.tee if shot_number == 1 else Lie.fairway,
                    "end_lie": Lie.hole if holed else Lie.green if putt else Lie.fairway,
                    "start_distance_yards": max(4.0, 400.0 - shot_number * 90 + rng.uniform(-20, 20)),
                    # A holed shot is at the hole: distance must be exactly 0,
                    # or the SG benchmark lookup is asked for "expected strokes
                    # from 40 yards, in the hole".
                    "end_distance_yards": 0.0 if holed else max(1.0, 400.0 - (shot_number + 1) * 90),
                    "strokes_gained": rng.uniform(-0.6, 0.4),
                    "tag": None,
                    "location": None,
                })
    session.execute(Shot.__table__.insert(), shot_rows)
    session.commit()

    practice = PracticeSession(user_id=user.id, source="R10")
    session.add(practice)
    session.commit()
    session.refresh(practice)
    session.execute(
        PracticeShot.__table__.insert(),
        [{"session_id": practice.id, "club": rng.choice(CLUBS[:-1]),
          "smash_factor": rng.uniform(1.1, 1.5), "carry_yards": rng.uniform(90, 270),
          "spin_axis_deg": rng.uniform(-4, 4), "club_path_deg": rng.uniform(-3, 3),
          "face_angle_deg": rng.uniform(-3, 3)} for _ in range(400)],
    )
    session.commit()

    print(f"  {email}: {len(round_ids)} rounds, {len(shot_rows)} shots")
    return user


def _seed(engine: Engine, rounds: int) -> tuple[User, int]:
    rng = random.Random(20260816)
    with Session(engine) as session:
        course = Course(name="Benchmark Links", city="Nowhere", state="SC")
        session.add(course)
        session.commit()
        session.refresh(course)

        holes = [Hole(course_id=course.id, number=n, par=par, yardage=yards)
                 for n, (par, yards) in enumerate(HOLE_LAYOUT, start=1)]
        session.add_all(holes)
        session.commit()
        hole_ids = [h.id for h in holes]

        user = _seed_user(session, "bench@example.com", course.id, hole_ids, rounds, rng)
        _seed_user(session, "other@example.com", course.id, hole_ids, rounds, rng)

        latest = session.exec(
            select(Round.id).where(Round.user_id == user.id).order_by(Round.played_at.desc())
        ).first()
        return user, latest


def _time(client: TestClient, method: str, path: str, repeats: int = 5) -> tuple[float, int]:
    timings = []
    status = 0
    for _ in range(repeats):
        started = time.perf_counter()
        response = client.request(method, path)
        timings.append((time.perf_counter() - started) * 1000)
        status = response.status_code
    return statistics.median(timings), status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--reuse", action="store_true", help="skip reseeding")
    args = parser.parse_args()

    url = _bench_database_url()
    print(f"Benchmark database: {url.database}")
    engine = _provision(url)

    if not args.reuse:
        _wipe(engine)
        print(f"Seeding {args.rounds} rounds per user…")
        started = time.perf_counter()
        user, latest_round = _seed(engine, args.rounds)
        print(f"  seeded in {time.perf_counter() - started:.1f}s")
    else:
        with Session(engine) as session:
            user = session.exec(select(User).where(User.email == "bench@example.com")).one()
            latest_round = session.exec(
                select(Round.id).where(Round.user_id == user.id).order_by(Round.played_at.desc())
            ).first()

    with Session(engine) as session:
        bench_user = session.get(User, user.id)

        def _override_session():
            yield session

        app.dependency_overrides[get_session] = _override_session
        # Sidesteps password hashing and cookies — this measures query cost,
        # not the login flow.
        app.dependency_overrides[get_current_user] = lambda: bench_user

        with TestClient(app) as client:
            endpoints = [
                ("GET", "/api/rounds"),
                ("GET", "/api/rounds?limit=1"),
                ("GET", f"/api/rounds/{latest_round}/analytics"),
                ("GET", f"/api/rounds/{latest_round}/holes"),
                ("GET", "/api/bag"),
                ("GET", "/api/practice/delivery"),
                ("GET", "/api/practice/combines"),
                ("GET", "/api/me/export"),
            ]
            print(f"\n{'endpoint':<45} {'median ms':>10}  status")
            for method, path in endpoints:
                median, status = _time(client, method, path)
                print(f"{method + ' ' + path:<45} {median:>10.1f}  {status}")

        app.dependency_overrides.clear()

    engine.dispose()


if __name__ == "__main__":
    main()
