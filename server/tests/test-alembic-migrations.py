from sqlalchemy import text
from datetime import datetime

# This tests the whole migration chain down to up.
# It is parametrized to run on PostgreSQL and SQLite.
from pytest_alembic.tests import test_upgrade

def test_migration_8(alembic_engine, alembic_runner):
    """
    Migration no. 8 used to fail on SQLite. The whole migration chain
    is now tested using `pytest_alembic.tests.test_upgrade`.

    This additional test makes sure that the behavior for the migration
    no. 8 is consistent across engines (see conditional branching in
    server/alembic/versions8_add_named_permissions.py).
    """
    alembic_runner.migrate_up_before("8")

    alembic_runner.insert_into("permissions", dict(id=1,
                                                   resource="dummy_resource",
                                                   user_id="dummy_user_id",
                                                   resource_id=1,
                                                   permission="dummy_permission",
                                                   created=datetime(2026, 2, 26)))
    alembic_runner.migrate_up_one()

    with alembic_engine.connect() as conn:
        rows = conn.execute(text("SELECT value FROM permissions")).fetchall()

    assert 1 == len(rows), "There should only be one entry in the test database"
    assert "1" == rows[0][0], "Value should be a coalescence of resource_id and resource_name"

    with alembic_engine.connect() as conn:
        conn.execute(text("""UPDATE permissions
                          SET
                          resource_id = NULL,
                          resource_name = 'dummy_name'
                          WHERE id = 1"""))
        conn.commit()
        rows = conn.execute(text("SELECT resource_id, resource_name FROM permissions WHERE id = 1")).fetchall()

    assert None == rows[0][0], "resource_id should have been updated"
    assert "dummy_name" == rows[0][1], "resource_name should have been updated"

    with alembic_engine.connect() as conn:
        rows = conn.execute(text("SELECT value FROM permissions WHERE id = 1")).fetchall()

    assert "dummy_name" == rows[0][0], "Value should be a coalescence of resource_id and resource_name"
