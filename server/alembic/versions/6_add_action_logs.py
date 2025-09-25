"""Add action logs

Revision ID: 6
Revises: 5
Create Date: 2025-10-10 17:20:14.155514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6'
down_revision: Union[str, None] = '5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('action_logs',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('action_id', sa.String(), nullable=False),
    sa.Column('mac_address', sa.String(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('action_logs')
