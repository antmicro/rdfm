"""Permissions based on name

Revision ID: 8
Revises: 7
Create Date: 2024-11-14 12:43:27.073314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8'
down_revision: Union[str, None] = '7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade_postgres() -> None:
    op.alter_column('permissions', 'resource_id', existing_type=sa.Integer(), nullable=True)
    op.add_column('permissions', sa.Column('resource_name', sa.String(), nullable=True))
    op.add_column('permissions', sa.Column(
        'value',
        sa.String(),
        sa.Computed("COALESCE(resource_id::text, resource_name)", persisted=True),
        nullable=False
    ))
    op.create_check_constraint(
        "at_least_one_not_null",
        "permissions",
        "resource_id IS NOT NULL OR resource_name IS NOT NULL"
    )
    op.drop_constraint(
        "unique_permission",
        "permissions",
        type_="unique"
    )
    op.create_unique_constraint(
        "unique_permission",
        "permissions",
        ["user_id", "resource", "permission", "value"],
    )


def upgrade_sqlite() -> None:
    op.create_table('permissions_new',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('resource', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=True), # make nullable
    sa.Column('resource_name', sa.String(), nullable=True),
    sa.Column('permission', sa.String(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column(
        'value',
        sa.String(),
        sa.Computed("COALESCE(CAST(resource_id AS TEXT), resource_name)", persisted=True),
        nullable=False
    ),
    sa.UniqueConstraint('user_id', 'resource', 'permission', 'value', name='unique_permission'),
    sa.CheckConstraint('resource_id IS NOT NULL OR resource_name IS NOT NULL', name= 'at_least_one_not_null'),
    sa.PrimaryKeyConstraint('id'),
    )

    try:
        # Select all values from the old table and insert them into the new table.
        # The previously non-existent `resource_name` is going to be set to NULL.
        op.rename_table('permissions', 'permissions_old')
        op.execute('''INSERT INTO permissions_new (resource, user_id, resource_id, resource_name, permission, created)
                   SELECT resource, user_id, resource_id, NULL, permission, created FROM permissions_old''')
    except Exception as e:
        # If anything goes wrong, try reverting to the previous state before re-raising the exception.

        # Check if the rename went through, if yes, revert.
        conn = op.get_bind()
        inspector = sa.engine.reflection.Inspector.from_engine(conn)
        if 'permissions_old' in inspector.get_table_names():
            op.rename_table('permissions_old', 'permissions')

        op.drop_table('permissions_new')

        raise e
    # Provided everything goes fine, drop `permissions_old` and rename `permissions_new` to just `permissions`.
    op.rename_table('permissions_new', 'permissions')
    op.drop_table('permissions_old')


def upgrade() -> None:
    bind = op.get_bind()
    if bind.engine.name == 'sqlite':
        upgrade_sqlite()
    elif bind.engine.name == 'postgresql':
        upgrade_postgres()
    else:
        raise RuntimeError(f'Engine name "{bind.engine.name}" not recognized')


def downgrade() -> None:
    # There is no sane way to handle this downgrade without data loss
    raise NotImplementedError('Downgrade from 8 to 7 not supported')
