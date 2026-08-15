"""course osm_relation_id

Revision ID: 9c1f4e7a2b83
Revises: 7d4a2e8c6f31
Create Date: 2026-08-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1f4e7a2b83'
down_revision: Union[str, Sequence[str], None] = '7d4a2e8c6f31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('course', sa.Column('osm_relation_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_course_osm_relation_id'), 'course', ['osm_relation_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_course_osm_relation_id'), table_name='course')
    op.drop_column('course', 'osm_relation_id')
