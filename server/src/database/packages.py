import sqlite3
import time
import os
import json
import datetime
from typing import Optional, List
import models.package
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData


class PackagesDB:
    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db


    def fetch_all(self) -> List[models.package.Package]:
        """Fetches all packages from the database
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    select(models.package.Package)
                )
                packages = session.scalars(stmt)
                if packages is None:
                    return []
                return [x for x in packages]
        except Exception as e:
            print("Package fetch failed:", repr(e))
            return []


    def create(self, package: models.package.Package) -> bool:
        """Creates a new package

        Returns:
            Whether the operation was successful
        """
        try:
            with Session(self.engine) as session:
                session.add(package)
                session.commit()
                return True
        except Exception as e:
            print("Package creation failed:", repr(e))
            return False


    def fetch_one(self, identifier: int) -> Optional[models.package.Package]:
        """ Fetches a package with the specified ID
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    select(models.package.Package)
                    .where(models.package.Package.id == identifier)
                )
                return session.scalar(stmt)
        except Exception as e:
            print("Package fetch failed:", repr(e))
            return None


    def delete(self, identifier: int) -> bool:
        """ Delete a package with the specified ID
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    delete(models.package.Package)
                    .where(models.package.Package.id == identifier)
                )
                session.execute(stmt)
                session.commit()
                return True
        except Exception as e:
            print("Package deletion failed:", repr(e))
            return False
