"""indexes and cascade deletes

Phase 11. Two things the original schema missed.

**Indexes.** `round.user_id`, `shot.round_id`, `shot.hole_id` and
`hole.course_id` are the columns every analytics, Smart Bag and practice
query filters on, and none of them were indexed — the initial migration
created the foreign keys without them. (Later migrations *did* index
`practice_session.user_id` and `practice_shot.session_id`, so this is an
oversight in the original tables rather than a deliberate policy.)

**ON DELETE CASCADE** on the ownership foreign keys, so deleting a user is
one statement instead of loading every child row into Python to delete it
individually (`app/api/routes/privacy.py`). Deliberately *not* applied to
`shot.hole_id`, `hole.course_id` or `round.course_id`: courses and holes are
shared reference geometry that other players' rounds may reference, and
DATA_PRIVACY.md is explicit that deleting one user must not delete them.

Revision ID: a91c4d6e2f57
Revises: 5b1e73f0c4a8
Create Date: 2026-08-16 02:31:44.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a91c4d6e2f57'
down_revision: Union[str, Sequence[str], None] = '5b1e73f0c4a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (constraint, table, column, referenced table, referenced column)
_CASCADE_FKS = [
    ("round_user_id_fkey", "round", "user_id", "user", "id"),
    ("shot_round_id_fkey", "shot", "round_id", "round", "id"),
    ("practice_session_user_id_fkey", "practice_session", "user_id", "user", "id"),
    ("practice_shot_session_id_fkey", "practice_shot", "session_id", "practice_session", "id"),
    ("virtual_round_user_id_fkey", "virtual_round", "user_id", "user", "id"),
    ("garmin_connection_user_id_fkey", "garmin_connection", "user_id", "user", "id"),
]

_INDEXES = [
    ("ix_round_user_id", "round", "user_id"),
    ("ix_shot_round_id", "shot", "round_id"),
    ("ix_shot_hole_id", "shot", "hole_id"),
    ("ix_hole_course_id", "hole", "course_id"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for name, table, column in _INDEXES:
        op.create_index(name, table, [column], unique=False)

    for name, table, column, ref_table, ref_column in _CASCADE_FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, ref_table, [column], [ref_column], ondelete="CASCADE")


def downgrade() -> None:
    """Downgrade schema."""
    for name, table, column, ref_table, ref_column in _CASCADE_FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, ref_table, [column], [ref_column])

    for name, table, _column in _INDEXES:
        op.drop_index(name, table_name=table)
