from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import models.group
import models.device
import models.package
import models.permission
import server
from rdfm.permissions import GROUP_RESOURCE


class GroupsDB:
    """Wrapper class for managing group data and device-group assignment"""

    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db

    def fetch_all(self) -> List[models.group.Group]:
        """Fetches all groups from the database"""
        with Session(self.engine) as session:
            stmt = select(models.group.Group)
            groups = session.scalars(stmt)
            if groups is None:
                return []
            return [x for x in groups]

    def create(self, group: models.group.Group) -> Optional[str]:
        """Create a new group

        The provided group is updated with the database identifier
        """
        try:
            with Session(self.engine) as session:
                session.add(group)
                session.commit()
                session.refresh(group)
                return None
        except IntegrityError as e:
            return ("Conflict while adding group,"
                    "a group with the same priority may already exist")

    def fetch_one(self, identifier: int) -> Optional[models.group.Group]:
        """ Fetches information about the specific group from the database
        """
        with Session(self.engine) as session:
            stmt = select(models.group.Group).where(
                models.group.Group.id == identifier
            )
            return session.scalar(stmt)

    def fetch_assigned(self, identifier: int) -> List[models.device.Device]:
        """Fetches all devices assigned to the specified group

        Args:
            identifier: group identifier
        """
        with Session(self.engine) as session:
            return session.scalars(
                session.query(models.device.Device)
                .select_from(models.device.DeviceGroupAssignment)
                .where(
                    models.device.DeviceGroupAssignment.group_id == identifier
                )
                .join(models.device.Device)
            ).all()

    def delete(self, identifier: int) -> bool:
        """Deletes a group

        Deletes a group from the database. If any devices are assigned  to
        the group being removed, the delete will fail.

        Args:
            identifier: group identifier

        Returns:
            True if the delete was successful
        """
        try:
            with Session(self.engine) as session:
                stmt = delete(models.permission.Permission).where(
                    models.permission.Permission.resource == GROUP_RESOURCE
                ).where(
                    models.permission.Permission.resource_id == identifier)
                session.execute(stmt)
                stmt = delete(models.group.Group).where(
                    models.group.Group.id == identifier
                )
                session.execute(stmt)
                session.commit()
                return True
        except IntegrityError:
            # Constraint failed, the group is still used by some devices
            return False

    def modify_assignment(
        self, identifier: int, additions: List[int], removals: List[int]
    ) -> Optional[str]:
        """Modify assignment of devices to the specified group

        This modifies per-device group assignment, as described by two lists
        containing device identifiers of devices that will be added/removed
        from the group.

        This operation is atomic - if at any point an invalid device
        identifier is encountered, the transaction is aborted.

        This covers:
            - Any device identifier which does not match a registered device
            - Any device identifier in `additions` which already has an
              assigned group with the same priority as the one specified by
              `identifier`
            - Any device identifier in `removals` which is not currently
              assigned to the specified package

        Additions are evaluated first, followed by the removals.

        Args:
            identifier: group identifier
            additions: device identifiers which shall be added to the specified
                       group
            removals: device identifiers which shall be removed from specified
                      group
        """
        try:
            with Session(self.engine) as session:
                def make_assignment(group, device):
                    assignment = models.device.DeviceGroupAssignment()
                    assignment.group_id = group
                    assignment.device_id = device
                    return assignment

                # Additions
                current_group = self.fetch_one(identifier)

                for addition in additions:
                    if (
                        session.query(models.group.Group)
                        .select_from(models.device.DeviceGroupAssignment)
                        .where(
                            models.device.DeviceGroupAssignment.device_id ==
                            addition
                        )
                        .join(models.group.Group)
                        .where(
                            models.group.Group.priority ==
                            current_group.priority
                        )
                        .first() is not None
                    ):

                        return ("A group with the same priority "
                                "is already assigned to one of the devices "
                                "requested to be added")

                session.add_all(
                        [make_assignment(identifier, a) for a in additions]
                )
                session.commit()

                # Removals
                stmt = (
                    delete(models.device.DeviceGroupAssignment)
                    .where(
                        models.device.DeviceGroupAssignment.group_id ==
                        identifier
                    )
                    .where(
                        models.device.DeviceGroupAssignment.device_id.in_(
                            removals
                        )
                    )
                )
                session.execute(stmt)
                session.commit()

                return None

        except IntegrityError as e:
            return "conflict while assigning device, the device may not exist"

    def modify_package(self, group: int, packages: List[int]) -> Optional[str]:
        """Modify package assignment of the specified group

        Args:
            group: group identifier
            packages: list of package identifiers to assign to the group.
                      If None, package assignment is instead removed from
                      the group

        Returns:
            None: on success
            str: user-friendly error string explaining the failure
        """
        try:
            with Session(self.engine) as session:
                stmt = delete(models.group.GroupPackageAssignment).where(
                    models.group.GroupPackageAssignment.group_id == group
                )
                session.execute(stmt)

                def make_assignment(group, package):
                    assignment = models.group.GroupPackageAssignment()
                    assignment.group_id = group
                    assignment.package_id = package
                    return assignment

                session.add_all(
                    [make_assignment(group, pkg) for pkg in packages]
                )
                session.commit()
                return None
        except IntegrityError:
            return "conflict while assigning package, the package may " \
                   "not exist anymore"

    def fetch_assigned_packages(self, group: int) -> List[int]:
        """Fetches a list of package identifiers assigned to this group

        Args:
            group: group identifier
        """
        with Session(self.engine) as session:
            return session.scalars(
                select(models.group.GroupPackageAssignment.package_id).where(
                    models.group.GroupPackageAssignment.group_id == group
                )
            ).all()

    def fetch_assigned_data(self, group: int) -> List[models.package.Package]:
        """Fetches a list of packages assigned to this group.

        Args:
            group: group identifier
        """
        with Session(self.engine) as session:
            return session.scalars(
                session.query(models.package.Package)
                .select_from(models.group.GroupPackageAssignment)
                .where(models.group.GroupPackageAssignment.group_id == group)
                .join(models.package.Package)
            ).all()

    def update_priority(self, group: int, priority: int) -> Optional[str]:
        """ Updates the group priority

        The priority must be distinct among priorities of other groups to which
        devices assigned to this group are also assigned to. If this condition
        is not met, an error is returned and the priority is kept unmodified.

        Args:
            group: group identifier
            priority: group priority to set
        """

        with Session(self.engine) as session:
            devices = self.fetch_assigned(group)
            for device in devices:
                device_group_ids = server.instance._devices_db.fetch_groups(
                        device.id
                )
                for group_id in device_group_ids:
                    if (
                            session.query(models.group.Group)
                            .select_from(models.device.DeviceGroupAssignment)
                            .where(
                                models.device.DeviceGroupAssignment.device_id
                                == device.id
                            )
                            .join(models.group.Group)
                            .where(models.group.Group.priority == priority)
                            .where(models.group.Group.id != group)
                            .first() is not None
                    ):
                        return ("A group with the same priority "
                                "is already assigned to one of the devices "
                                "in this group")

            stmt = (
                update(models.group.Group)
                .values(priority=priority)
                .where(models.group.Group.id == group)
            )
            session.execute(stmt)
            session.commit()

    def update_policy(self, group: int, policy: str):
        """Updates the group update policy

        Args:
            group: group identifier
            policy: group update policy string to set
        """
        with Session(self.engine) as session:
            stmt = (
                update(models.group.Group)
                .values(policy=policy)
                .where(models.group.Group.id == group)
            )
            session.execute(stmt)
            session.commit()
