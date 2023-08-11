from typing import Optional, List, Any
from sqlalchemy import create_engine, select, update, delete, desc, null
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData
from sqlalchemy.exc import IntegrityError
import models.group
import models.device

class GroupsDB:
    """ Wrapper class for managing group data and device-group assignment
    """

    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db


    def fetch_all(self) -> List[models.group.Group]:
        """ Fetches all groups from the database
        """
        with Session(self.engine) as session:
            stmt = (
                select(models.group.Group)
            )
            groups = session.scalars(stmt)
            if groups is None:
                return []
            return [x for x in groups]


    def create(self, group: models.group.Group):
        """ Create a new group

        The provided group is updated with the database identifier
        """
        with Session(self.engine) as session:
            session.add(group)
            session.commit()
            session.refresh(group)


    def fetch_one(self, identifier: int) -> Optional[models.group.Group]:
        """ Fetches information about the specific group from the database
        """
        with Session(self.engine) as session:
            stmt = (
                select(models.group.Group)
                .where(models.group.Group.id == identifier)
            )
            return session.scalar(stmt)


    def fetch_assigned(self, identifier: int) -> List[models.device.Device]:
        """ Fetches all devices assigned to the specified group

        Args:
            identifier: group identifier
        """
        with Session(self.engine) as session:
            stmt = (
                select(models.device.Device)
                .where(models.device.Device.group == identifier)
            )
            devices = session.scalars(stmt)
            if devices is None:
                return []
            return [ x for x in devices ]


    def delete(self, identifier: int) -> bool:
        """ Deletes a group

        Deletes a group from the database. If any devices are assigned the group
        being removed, the delete will fail.

        Args:
            identifier: group identifier

        Returns:
            True if the delete was successful
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    delete(models.group.Group)
                    .where(models.group.Group.id == identifier)
                )
                session.execute(stmt)
                session.commit()
                return True
        except IntegrityError as e:
            # Constraint failed, the group is still used by some devices
            return False


    def modify_assignment(self, identifier: int, additions: List[int], removals: List[int]) -> Optional[str]:
        """ Modify assignment of devices to the specified group

        This modifies per-device group assignment, as described by two lists containing
        device identifiers of devices that will be added/removed from the group.

        This operation is atomic - if at any point an invalid device identifier is
        encountered, the transaction is aborted. This covers:
            - Any device identifier which does not match a registered device
            - Any device identifier in `additions` which already has an assigned group
            - Any device identifier in `removals` which is not currently assigned to the
              specified package

        Additions are evaluated first, followed by the removals.

        Args:
            identifier: group identifier
            additions: device identifiers which shall be added to the specified group
            removals: device identifiers which shall be removed from specified group
        """
        with Session(self.engine) as session:
            # Evaluate addition first
            stmt = (
                update(models.device.Device)
                .values(group = identifier)
                .where(models.device.Device.group.is_(None))
                .where(models.device.Device.id.in_(additions))
            )
            res = session.execute(stmt)
            if res.rowcount != len(additions):
                session.rollback()
                return "conflict while applying group additions, one of the provided device identifiers may not exist anymore or has already been assigned to a different group"

            # Now evaluate the removals
            stmt = (
                update(models.device.Device)
                .values(group = None)
                .where(models.device.Device.group == identifier)
                .where(models.device.Device.id.in_(removals))
            )
            res = session.execute(stmt)
            if res.rowcount != len(removals):
                session.rollback()
                return "conflict while applying group removals, one of the provided device identifiers may not exist anymore or trying to remove group from unassigned device"

            session.commit()
            return None


    def modify_package(self, group: int, package: Optional[int]) -> Optional[str]:
        """ Modify package assignment of the specified group

        Args:
            group: group identifier
            package: package identifier to assign to the group.
                     If None, package assignment is instead removed from the group

        Returns:
            None: on success
            str: user-friendly error string explaining the failure
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    update(models.group.Group)
                    .values(package_id = package)
                    .where(models.group.Group.id == group)
                )
                res = session.execute(stmt)
                if res.rowcount != 1:
                    session.rollback()
                    return "conflict while assigning package, the group may not exist anymore"

                session.commit()
                return None
        except IntegrityError as e:
            return "conflict while assigning package, the package may not exist anymore"
