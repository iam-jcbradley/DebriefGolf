"""garmin connection

Revision ID: 7d4a2e8c6f31
Revises: 3c7e5b1f9a20
Create Date: 2026-08-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7d4a2e8c6f31'
down_revision: Union[str, Sequence[str], None] = '3c7e5b1f9a20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'garmin_connection',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('access_token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('refresh_token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('token_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('scope', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('connected_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_garmin_connection_user_id'), 'garmin_connection', ['user_id'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_garmin_connection_user_id'), table_name='garmin_connection')
    op.drop_table('garmin_connection')
