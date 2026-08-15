"""strokes gained benchmark

Revision ID: 8f3c1a9d4b2e
Revises: 2e2dc73047fe
Create Date: 2026-08-15 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8f3c1a9d4b2e'
down_revision: Union[str, Sequence[str], None] = '2e2dc73047fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # `lie` enum type already exists (created by the initial migration for
    # shot.start_lie/end_lie) — reuse it, don't try to create it again.
    lie_enum = postgresql.ENUM(
        'tee', 'fairway', 'rough', 'sand', 'recovery', 'green', 'fringe', 'penalty', 'hole',
        name='lie', create_type=False,
    )
    op.create_table(
        'strokes_gained_benchmark',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('handicap_bucket', sa.Integer(), nullable=False),
        sa.Column('lie', lie_enum, nullable=False),
        sa.Column('distance_yards', sa.Float(), nullable=False),
        sa.Column('expected_strokes', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'handicap_bucket', 'lie', 'distance_yards',
            name='uq_sg_benchmark_bucket_lie_distance',
        ),
    )
    op.create_index(
        op.f('ix_strokes_gained_benchmark_handicap_bucket'),
        'strokes_gained_benchmark', ['handicap_bucket'],
    )
    op.create_index(
        op.f('ix_strokes_gained_benchmark_lie'),
        'strokes_gained_benchmark', ['lie'],
    )
    op.create_index(
        op.f('ix_strokes_gained_benchmark_distance_yards'),
        'strokes_gained_benchmark', ['distance_yards'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_strokes_gained_benchmark_distance_yards'), table_name='strokes_gained_benchmark'
    )
    op.drop_index(op.f('ix_strokes_gained_benchmark_lie'), table_name='strokes_gained_benchmark')
    op.drop_index(
        op.f('ix_strokes_gained_benchmark_handicap_bucket'), table_name='strokes_gained_benchmark'
    )
    op.drop_table('strokes_gained_benchmark')
