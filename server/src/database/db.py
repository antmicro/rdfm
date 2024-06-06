from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy_utils.functions import database_exists
from models.base import Base
from alembic import config, script, command
from alembic.runtime import migration
import os.path

# Import all models below


def check_current_head(alembic_cfg, connectable):
    # type: (config.Config, engine.Engine) -> bool
    directory = script.ScriptDirectory.from_config(alembic_cfg)
    with connectable.begin() as connection:
        context = migration.MigrationContext.configure(connection)
        return set(context.get_current_heads()) == set(directory.get_heads())


def create(connstring: str) -> Engine:
    """Creates a connection to the database used to store server data

    Args:
        connstring: SQLAlchemy database connection string. For reference,
                    see: https://docs.sqlalchemy.org/en/20/core/engines.html
    Returns:
        SQLAlchemy Engine object that can be used to query the database
        or None, if database creation/connection failed
    """
    try:
        db: Engine = create_engine(connstring, echo=True)

        if db.url.drivername == "sqlite":
            # SQLite: Automatically enable foreign keys when connecting
            # to the DB. We use foreign keys for maintaining integrity
            # for packages/groups
            def _fk_pragma_on_connect(dbapi_con, con_record):
                dbapi_con.execute("pragma foreign_keys=ON")

            event.listen(db, "connect", _fk_pragma_on_connect)

        if os.path.isfile('alembic.ini'):
            # If the database exists but is not managed by alembic,
            # we assume it is the initial version and stamp it as such.
            if (
                database_exists(connstring) and
                not inspect(db).has_table("alembic_version")
            ):
                alembic_args = [
                    '-x', f'dbPath={connstring}',
                    '--raiseerr',
                    'stamp', '1',
                ]
                config.main(argv=alembic_args)

            # Create/migrate the database
            #
            # If the database exists but is out of sync, it will be migrated to
            # latest layout, if it does not exist it will be created and will
            # go through the migrations to the most recent layout.
            alembic_cfg = config.Config('alembic.ini')
            if not check_current_head(alembic_cfg, db):
                alembic_args = [
                    '-x', f'dbPath={connstring}',
                    '--raiseerr',
                    'upgrade', 'head',
                ]
                config.main(argv=alembic_args)
        else:
            # Fall back to unmanaged DB if alembic.ini is missing
            print("alembic.ini missing, using unmanaged database")
            Base.metadata.create_all(db)

        return db
    except Exception as e:
        print("Database initialization failed:", repr(e))
        return None
