from typing import Optional
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy_utils.functions import database_exists
from models.base import Base
from alembic import config, script, command
from alembic.runtime import migration
import os.path
import pathlib

# Import all models below

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = pathlib.Path(os.path.join(CURRENT_PATH, '../../')).resolve()


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

        inipath: Optional[pathlib.Path] = None
        if os.path.isfile(ROOT_PATH / 'alembic.ini'):
            inipath = ROOT_PATH / 'alembic.ini'
        elif os.path.isfile(ROOT_PATH / 'deploy' / 'alembic.ini'):
            inipath = ROOT_PATH / 'deploy' / 'alembic.ini'

        scriptpath: Optional[pathlib.Path] = None
        if os.path.isdir(ROOT_PATH / 'alembic'):
            scriptpath = ROOT_PATH / 'alembic'

        print(f"""Creation of database connection: assuming locations:
              \t*configuration file: {inipath}
              \t*alembic scripts directory: {scriptpath}""")

        if inipath is not None:
            alembic_cfg = config.Config(inipath.resolve())
            if scriptpath:  # If scriptpath not available it will be pulled from alembic.ini
                alembic_cfg.set_main_option("script_location", str(scriptpath.resolve()))
            alembic_cfg.set_main_option("sqlalchemy.url", connstring)

            # If the database exists, is not empty,
            # and is not managed by alembic, we assume it is
            # the initial version and stamp it as such.
            if (
                database_exists(connstring) and
                len(inspect(db).get_table_names()) > 0 and
                not inspect(db).has_table("alembic_version")
            ):
                command.stamp(alembic_cfg, "1")

            # Create/migrate the database
            #
            # If the database exists but is out of sync, it will be migrated to
            # latest layout, if it does not exist it will be created and will
            # go through the migrations to the most recent layout.
            if not check_current_head(alembic_cfg, db):
                command.upgrade(alembic_cfg, "head")
        else:
            # Fall back to unmanaged DB if alembic.ini is missing
            print("alembic.ini missing, using unmanaged database")
            Base.metadata.create_all(db)

        return db
    except Exception as e:
        print("Database initialization failed:", repr(e))
        return None
