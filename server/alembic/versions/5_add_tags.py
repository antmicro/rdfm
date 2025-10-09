"""Add device tags

Revision ID: 5
Revises: 4
Create Date: 2025-10-09 11:57:47.460255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5'
down_revision: Union[str, None] = '4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('devices_tags',
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('tag', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('device_id', 'tag')
    )


def downgrade() -> None:
    op.drop_table('devices_tags')
