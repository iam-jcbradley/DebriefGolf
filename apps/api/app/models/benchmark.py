from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.shot import Lie

HANDICAP_BUCKETS: list[int] = [0, 5, 10, 15, 20, 25]


class StrokesGainedBenchmark(SQLModel, table=True):
    """One (handicap bucket, lie, distance) -> expected-strokes-to-hole-out point.

    Populated by `app.services.benchmarks.generate_benchmark_rows()` (see
    `make seed`). The Strokes Gained engine (Phase 2) looks these up via
    `app.services.benchmarks.expected_strokes()` and interpolates between
    the seeded distance points for a given lie/bucket.
    """

    __tablename__: str = "strokes_gained_benchmark"
    __table_args__ = (
        UniqueConstraint(
            "handicap_bucket", "lie", "distance_yards", name="uq_sg_benchmark_bucket_lie_distance"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    handicap_bucket: int = Field(index=True)
    lie: Lie = Field(index=True)
    distance_yards: float = Field(index=True)
    expected_strokes: float
