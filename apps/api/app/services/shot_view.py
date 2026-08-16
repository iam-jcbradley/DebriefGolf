"""The subset of a shot the aggregate analytics actually read.

Smart Bag gapping, putting mechanics and combine detection each walk *every*
shot a player has ever recorded. Loading those as full `Shot` ORM instances
costs roughly 5x what selecting the handful of columns they read does — at
20k shots that was the difference between a ~340ms query and a ~70ms one,
and it dominated the cost of `GET /bag` and both practice endpoints.

So those routes select raw columns instead, and the services accept anything
with these attributes. A `Shot` satisfies it, and so does the row of a
`select(Shot.club, Shot.start_distance_yards, ...)` — SQLAlchemy names row
attributes after the columns.

This is only worth doing where the query is "all of this user's shots".
Single-round endpoints load full `Shot` objects as before; the difference
there is a few dozen rows.
"""

from typing import Protocol

from app.models.shot import Lie


class ShotView(Protocol):
    club: str | None
    start_distance_yards: float
    end_distance_yards: float
    end_lie: Lie
    strokes_gained: float | None
