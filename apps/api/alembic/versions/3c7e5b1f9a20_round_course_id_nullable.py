"""round course_id nullable

Revision ID: 3c7e5b1f9a20
Revises: 8f3c1a9d4b2e
Create Date: 2026-08-22 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c7e5b1f9a20'
down_revision: Union[str, Sequence[str], None] = '8f3c1a9d4b2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('round', 'course_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('round', 'course_id', existing_type=sa.Integer(), nullable=False)
