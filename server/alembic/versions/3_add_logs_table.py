"""Add logs table

Revision ID: 3
Revises: 2
Create Date: 2024-07-25 10:13:47.069428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3'
down_revision: Union[str, None] = '2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),                
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('device_timestamp', sa.DateTime(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('entry', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('logs')
