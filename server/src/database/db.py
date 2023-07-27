import os
from sqlalchemy import create_engine, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData
from typing import Optional
import models


def create(filepath: str) -> Engine:
    """Creates connection to device database and creates table if it does not exist

    Returns:
        SQLAlchemy Engine object that can be used to query the database
        or None, if database creation/connection failed
    """
    try:
        db: Engine = create_engine(f"sqlite:///{filepath}", echo=True)
        # This actually creates all the tables in the database for entities that inherit from models.device.Base
        models.device.Base.metadata.create_all(db)
        return db
    except Exception as e:
        print("Database initialization failed:", repr(e))
        return None
