"""Add download URL for action logs in storage.

Revision ID: 9
Revises: 8
Create Date: 2025-12-04 12:29:36.464904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9'
down_revision: Union[str, None] = '8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('action_logs', sa.Column('download_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('action_logs', 'download_url')
