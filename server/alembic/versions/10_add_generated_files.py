"""Add generated files DB

Revision ID: 10
Revises: 9
Create Date: 2026-10-27 08:43:08.072123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '10'
down_revision: Union[str, None] = '9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('generated_files',
    sa.Column('exec_id', sa.String(), nullable=False),
    sa.Column('filename', sa.String(), nullable=False),
    sa.Column('download_url', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('exec_id', 'filename'),
    sa.ForeignKeyConstraint(['exec_id'], ['action_logs.id'], ondelete='CASCADE')
    )


def downgrade() -> None:
    op.drop_table('generated_files')
