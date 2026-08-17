"""`club_carry_dispersion_sql` (Phase 16) must produce the exact same
numbers `app/services/smart_bag.py`'s `reject_outliers_iqr` +
`compute_dispersion` do on the same samples — this is a SQL rewrite of
those functions' outlier fence, not a new one, so any drift here is a
correctness bug. `tests/test_bag_route.py`'s outlier scenario is
duplicated at this lower level so a future SQL change gets caught before
it reaches the endpoint.
"""

from sqlmodel import Session

from app.api.routes._shot_queries import club_carry_dispersion_sql
from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User
from app.services.smart_bag import compute_dispersion


def _seed_shots(session: Session, user: User, carries_by_club: dict[str, list[float]]) -> None:
    course = Course(name="Query Test Course")
    session.add(course)
    session.commit()
    session.refresh(course)

    hole = Hole(course_id=course.id, number=1, par=4, yardage=400)
    session.add(hole)
    session.commit()
    session.refresh(hole)

    round_ = Round(
        user_id=user.id, course_id=course.id, total_score=90, status=RoundStatus.verified
    )
    session.add(round_)
    session.commit()
    session.refresh(round_)

    shot_number = 1
    for club, carries in carries_by_club.items():
        for carry in carries:
            session.add(
                Shot(
                    round_id=round_.id, hole_id=hole.id, shot_number=shot_number, club=club,
                    start_lie=Lie.tee, end_lie=Lie.fairway,
                    start_distance_yards=400, end_distance_yards=400 - carry,
                )
            )
            shot_number += 1
    session.commit()


class TestClubCarryDispersionSql:
    def test_matches_python_dispersion_with_outlier(
        self, db_session: Session, user: User
    ) -> None:
        samples = [248.0, 250.0, 252.0, 251.0, 249.0, 400.0]  # 400 is a bogus outlier
        _seed_shots(db_session, user, {"Driver": samples})

        result = club_carry_dispersion_sql(db_session, user.id)
        expected = compute_dispersion(samples)

        stats = result["Driver"]
        assert stats.count == expected.count == 5
        assert stats.excluded_outliers == expected.excluded_outliers == 1
        assert stats.mean == expected.mean == 250.0
        assert stats.median == expected.median
        assert abs(stats.stdev - expected.stdev) < 1e-9

    def test_below_min_samples_for_iqr_keeps_everything(
        self, db_session: Session, user: User
    ) -> None:
        samples = [150.0, 200.0, 5000.0]  # only 3 samples, below MIN_SAMPLES_FOR_IQR
        _seed_shots(db_session, user, {"7-Iron": samples})

        result = club_carry_dispersion_sql(db_session, user.id)
        expected = compute_dispersion(samples)

        assert result["7-Iron"].count == expected.count == 3
        assert result["7-Iron"].excluded_outliers == 0
        assert result["7-Iron"].mean == expected.mean

    def test_at_min_samples_for_iqr_boundary_still_rejects_outlier(
        self, db_session: Session, user: User
    ) -> None:
        # Exactly MIN_SAMPLES_FOR_IQR (4) samples, with a real outlier among
        # them — pins down the `n >= MIN_SAMPLES_FOR_IQR` boundary in the
        # SQL's `case()` fence, which no other test exercises with an
        # outlier actually present at exactly the threshold.
        samples = [148.0, 150.0, 152.0, 400.0]
        _seed_shots(db_session, user, {"Driver": samples})

        result = club_carry_dispersion_sql(db_session, user.id)
        expected = compute_dispersion(samples)

        assert expected.excluded_outliers == 1  # sanity: the fixture is a real boundary case
        stats = result["Driver"]
        assert stats.count == expected.count
        assert stats.excluded_outliers == expected.excluded_outliers
        assert stats.mean == expected.mean
        assert stats.median == expected.median
        assert abs(stats.stdev - expected.stdev) < 1e-9

    def test_excludes_empty_string_club(self, db_session: Session, user: User) -> None:
        # shot_carry_distance's `if not shot.club` treats "" the same as
        # None — the SQL filter has to match that, not just `IS NOT NULL`.
        _seed_shots(db_session, user, {"": [150.0, 152.0, 148.0, 151.0]})

        assert club_carry_dispersion_sql(db_session, user.id) == {}

    def test_multiple_clubs_computed_independently(
        self, db_session: Session, user: User
    ) -> None:
        _seed_shots(
            db_session,
            user,
            {
                "Driver": [250.0, 255.0, 245.0, 248.0],
                "7-Iron": [150.0, 152.0, 148.0, 151.0],
            },
        )

        result = club_carry_dispersion_sql(db_session, user.id)

        assert set(result) == {"Driver", "7-Iron"}
        assert result["Driver"].mean == 249.5
        assert result["7-Iron"].mean == 150.25

    def test_empty_for_a_user_with_no_shots(self, db_session: Session, user: User) -> None:
        assert club_carry_dispersion_sql(db_session, user.id) == {}

    def test_ignores_another_users_shots(
        self, db_session: Session, user: User, other_user: User
    ) -> None:
        _seed_shots(db_session, other_user, {"Driver": [250.0, 255.0, 245.0, 248.0]})

        assert club_carry_dispersion_sql(db_session, user.id) == {}

    def test_excludes_putter(self, db_session: Session, user: User) -> None:
        _seed_shots(db_session, user, {"Putter": [5.0, 4.0, 6.0, 5.5]})

        assert club_carry_dispersion_sql(db_session, user.id) == {}

    def test_excludes_non_positive_carry(self, db_session: Session, user: User) -> None:
        # Negative "carry" (end farther from the hole than start) shouldn't
        # happen in real data but must not be counted as a sample if it does
        # — matches shot_carry_distance's callers, which all filter `> 0`.
        _seed_shots(db_session, user, {"Driver": [-5.0, 0.0]})

        assert club_carry_dispersion_sql(db_session, user.id) == {}
