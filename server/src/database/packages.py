from typing import Optional, List
import models.package
import models.group
from sqlalchemy import select, delete, desc
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rdfm.schema.v1.updates import META_DEVICE_TYPE
import models.permission
from rdfm.permissions import PACKAGE_RESOURCE


class PackagesDB:
    """Wrapper class for managing package data stored in the database"""

    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db

    def fetch_all(self) -> List[models.package.Package]:
        """Fetches all packages from the database"""
        try:
            with Session(self.engine) as session:
                stmt = select(models.package.Package)
                packages = session.scalars(stmt)
                if packages is None:
                    return []
                return [x for x in packages]
        except Exception as e:
            print("Package fetch failed:", repr(e))
            return []

    def create(self, package: models.package.Package) -> bool:
        """Creates a new package

        Args:
            package: package to create

        Returns:
            True the operation was successful
        """
        try:
            with Session(self.engine) as session:
                session.add(package)
                session.commit()
                session.refresh(package)
                return True
        except Exception as e:
            print("Package creation failed:", repr(e))
            return False

    def fetch_one(self, identifier: int) -> Optional[models.package.Package]:
        """Fetches a package with the specified ID

        Args:
            identifier: numeric ID of the package
        """
        try:
            with Session(self.engine) as session:
                stmt = select(models.package.Package).where(
                    models.package.Package.id == identifier
                )
                return session.scalar(stmt)
        except Exception as e:
            print("Package fetch failed:", repr(e))
            return None

    def fetch_compatible(self, devtype: str) -> List[models.package.Package]:
        """Fetches a list of packages compatible with the specified device
           type, sorted by their creation date (most recent first)

        Args:
            devtype: device type used to search for compatible packages.
                     This is compared with the `rdfm.hardware.devtype` entry
                     in package metadata to determine if a package is
                     compatible.
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    select(models.package.Package)
                    .where(
                        models.package.Package.info[
                            META_DEVICE_TYPE
                        ].as_string()
                        == devtype
                    )
                    .order_by(desc(models.package.Package.created))
                )
                packages = session.scalars(stmt)
                print(packages)
                if packages is None:
                    return []
                return [x for x in packages]
        except Exception as e:
            print("Package fetch failed:", repr(e))
            return []

    def fetch_groups(self, identifier: int) -> List[int]:
        """Fetch IDs of groups the package with a given identifier
        is assigned to
        """
        with Session(self.engine) as session:
            return session.scalars(
                select(models.group.GroupPackageAssignment.group_id)
                .where(
                    models.group.GroupPackageAssignment.package_id == identifier
                )
            ).all()

    def delete(self, identifier: int) -> bool:
        """Delete a package with the specified ID

        Args:
            identifier: numeric ID of the package
        """
        try:
            with Session(self.engine) as session:
                stmt = delete(
                    models.permission.Permission).where(
                        models.permission.Permission.resource == PACKAGE_RESOURCE
                    ).where(
                        models.permission.Permission.resource_id == identifier)
                session.execute(stmt)
                stmt = delete(models.package.Package).where(
                    models.package.Package.id == identifier
                )
                session.execute(stmt)
                session.commit()
                return True
        except IntegrityError:
            # Constraint failed, the package is assigned to an existing group
            return False
