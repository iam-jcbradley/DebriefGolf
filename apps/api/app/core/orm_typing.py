"""Two narrow escape hatches for real, well-understood gaps between what
SQLModel actually does at runtime and what pyright can see statically
(Phase 17, `docs/DEVELOPMENT_PLAN.md`). Neither papers over a real bug —
each names the exact stub gap it works around, per this repo's own
convention for suppressions.

`persisted()` — a SQLModel primary/foreign key is typed `int | None`
(`None` before the row is inserted), so every route handler reading
`row.id`/`row.user_id`/etc. off a row it just fetched or just
committed+refreshed hits a `reportArgumentType` mismatch against a
downstream parameter typed plain `int` — even though that row is, in
every one of these call sites, already persisted. This narrows the type
at the boundary instead of scattering ~60 individual ignores; the
`AssertionError` it can raise would itself be a real bug (a route reading
an id off a row that was never actually saved), not a case this file
expects to hit.

`col()` — SQLModel's `Field`-declared class attributes are annotated with
their plain Python type (`Shot.id` types as `int | None`, not
`InstrumentedAttribute[int]`) so Pydantic can validate instances with
them; pyright takes that literally at the *class* level too, where the
real runtime value is SQLAlchemy's column-expression descriptor. This is
a long-standing upstream SQLModel/pyright gap (there is no `Mapped[]`
annotation SQLModel can use without breaking the Pydantic side), not
anything specific to this codebase. `col()` is `Any`-typed identity: reach
for it only at query-construction call sites (`.order_by()`, `.join()`,
`.is_not()`, `.in_()`, comparisons used as join predicates) where pyright
is flatly wrong about what `SomeModel.column` is, never to paper over an
actual type mismatch.
"""

from typing import Any


def persisted[T](id_: T | None) -> T:
    if id_ is None:
        raise AssertionError("expected a persisted row to have an id")
    return id_


def col(attr: Any) -> Any:
    return attr
