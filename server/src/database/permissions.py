from typing import Optional, List
from sqlalchemy import select, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import models.permission


class PermissionsDB:
    """Wrapper class for managing permissions"""

    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db

    def fetch_all(self, user_id: Optional[str] = None) -> List[models.permission.Permission]:
        """Fetches all permissions from the database"""
        with Session(self.engine) as session:
            stmt = select(models.permission.Permission)

            if user_id is not None:
                stmt = stmt.where(models.permission.Permission.user_id == user_id)

            permissions = session.scalars(stmt)
            if permissions is None:
                return []
            return [x for x in permissions]

    def create(
        self, permission: models.permission.Permission
    ) -> Optional[str]:
        """Create a new permission
        """
        try:
            with Session(self.engine) as session:
                session.add(permission)
                session.commit()
                session.refresh(permission)
                return None
        except IntegrityError as e:
            return "Conflict while adding a permission"

    def fetch_one(
        self, identifier: int
    ) -> Optional[models.permission.Permission]:
        """ Fetches information about the specific permission
            from the database
        """
        with Session(self.engine) as session:
            stmt = select(models.permission.Permission).where(
                models.permission.Permission.id == identifier)
            return session.scalar(stmt)

    def fetch_one_by_attributes(
        self, resource: str, user_id: str, resource_id: int, permission: str
    ) -> Optional[models.permission.Permission]:
        """ Fetches information about the specific permission
            using attributes from the database
        """
        with Session(self.engine) as session:
            stmt = select(models.permission.Permission).where(
                models.permission.Permission.user_id == user_id
            ).where(
                models.permission.Permission.resource_id == resource_id
            ).where(
                models.permission.Permission.permission == permission
            ).where(
                models.permission.Permission.resource == resource)
            return session.scalar(stmt)

    def fetch_named_by_attributes(
        self, resource: str, user_id: str, permission: str
    ) -> List[str]:
        """ Fetches information about named permissions
            using attributes from the database
        """
        with Session(self.engine) as session:
            return session.scalars(
                select(models.permission.Permission.resource_name).where(
                    models.permission.Permission.user_id == user_id
                ).where(
                    models.permission.Permission.resource_name.is_not(None)
                ).where(
                    models.permission.Permission.permission == permission
                ).where(
                    models.permission.Permission.resource == resource)
            ).all()

    def delete(self, identifier: int) -> bool:
        """Deletes a permission from the database

        Args:
            identifier: permission identifier

        Returns:
            True if the delete was successful
        """
        try:
            with Session(self.engine) as session:
                stmt = delete(models.permission.Permission).where(
                    models.permission.Permission.id == identifier)
                session.execute(stmt)
                session.commit()
                return True
        except IntegrityError:
            return False

    def delete_permission_by_attrs(self, resource, resource_id, user_id, permission):
        try:
            with Session(self.engine) as session:
                stmt = delete(models.permission.Permission).where(
                    models.permission.Permission.user_id == user_id
                ).where(
                    models.permission.Permission.resource_id == resource_id
                ).where(
                    models.permission.Permission.resource == resource)
                session.execute(stmt)
                session.commit()
                return True
        except IntegrityError:
            return False
