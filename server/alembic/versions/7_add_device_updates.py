"""Add device updates

Revision ID: 7
Revises: 6
Create Date: 2025-10-30 18:02:51.759098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7'
down_revision: Union[str, None] = '6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('device_updates',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('mac_address', sa.String(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('version', sa.String(), nullable=False),
    sa.Column('progress', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('device_updates')
