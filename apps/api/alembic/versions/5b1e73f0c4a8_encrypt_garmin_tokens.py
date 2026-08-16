"""encrypt garmin tokens

Phase 10: `garmin_connection.access_token`/`refresh_token` stored the OAuth
tokens as plain strings. They now hold Fernet ciphertext (app/core/crypto.py),
so the columns are renamed to make the change visible at the schema level —
a plaintext token assigned to a column named `*_encrypted` reads as a bug.

Existing rows can't be migrated in place: the plaintext can be encrypted, but
this migration deliberately doesn't do that, because any row written before
this point has had its tokens sitting in the clear in the database (and in
every backup of it). Those tokens should be considered exposed and revoked
rather than carried forward, so the rows are deleted and affected users
reconnect Garmin — a single click that re-runs the OAuth flow, losing no golf
data. Nothing else references garmin_connection.

Revision ID: 5b1e73f0c4a8
Revises: 4286c9ba2925
Create Date: 2026-08-16 02:04:11.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5b1e73f0c4a8'
down_revision: Union[str, Sequence[str], None] = '4286c9ba2925'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("DELETE FROM garmin_connection"))
    op.alter_column('garmin_connection', 'access_token', new_column_name='access_token_encrypted')
    op.alter_column(
        'garmin_connection', 'refresh_token', new_column_name='refresh_token_encrypted'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Same reasoning in reverse: the ciphertext isn't a valid plaintext
    # token, so carrying rows back would leave unusable credentials behind.
    op.execute(sa.text("DELETE FROM garmin_connection"))
    op.alter_column('garmin_connection', 'access_token_encrypted', new_column_name='access_token')
    op.alter_column(
        'garmin_connection', 'refresh_token_encrypted', new_column_name='refresh_token'
    )
