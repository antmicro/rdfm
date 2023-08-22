import os
from sqlalchemy import create_engine, select, update, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData
from typing import Optional
from models.base import Base

# Import all models below
import models.device
import models.package

def create(connstring: str) -> Engine:
    """ Creates a connection to the database used to store server data

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
            # SQLite: Automatically enable foreign keys when connecting to the DB
            # We use foreign keys for maintaining integrity for packages/groups
            def _fk_pragma_on_connect(dbapi_con, con_record):
                dbapi_con.execute('pragma foreign_keys=ON')
            event.listen(db, 'connect', _fk_pragma_on_connect)

        # This actually creates all the tables in the database for entities that inherit from models.device.Base
        Base.metadata.create_all(db)
        return db
    except Exception as e:
        print("Database initialization failed:", repr(e))
        return None
