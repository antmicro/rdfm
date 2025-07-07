import json
import datetime
from typing import Optional, List
import models.device
import models.permission
from sqlalchemy import select, update, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import server
from rdfm.permissions import DEVICE_RESOURCE


class DevicesDB:
    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db

    def get_device_data(
        self, mac_address: str
    ) -> Optional[models.device.Device]:
        with Session(self.engine) as session:
            stmt = select(models.device.Device).where(
                models.device.Device.mac_address == mac_address
            )
            return session.scalar(stmt)

    def update_timestamp(self, mac_address: str, timestamp: datetime.datetime):
        """Update device's last healthcheck time in database"""
        with Session(self.engine) as session:
            stmt = (
                update(models.device.Device)
                .values(last_access=timestamp)
                .where(models.device.Device.mac_address == mac_address)
            )
            session.execute(stmt)
            session.commit()

    def fetch_all(self) -> List[models.device.Device]:
        """Fetch a list of all devices found in the database"""
        with Session(self.engine) as session:
            return session.scalars(select(models.device.Device)).all()

    def fetch_one(self, identifier: int) -> models.device.Device:
        """Fetch data of the device with a given identifier"""
        with Session(self.engine) as session:
            return session.scalar(
                select(models.device.Device).where(
                    models.device.Device.id == identifier
                )
            )

    def fetch_groups(self, identifier: int) -> List[int]:
        """Fetch IDs of groups the device with a given identifier
        is assigned to
        """
        with Session(self.engine) as session:
            return session.scalars(
                select(models.device.DeviceGroupAssignment.group_id)
                .where(
                    models.device.DeviceGroupAssignment.device_id == identifier
                )
            ).all()

    def fetch_active_group(self, identifier: int) -> Optional[int]:
        """ Fetch ID of the group that is active for the device with a given
        identifier
        """
        groups = self.fetch_groups(identifier)
        if not groups:
            return None

        prios = []
        for group_id in groups:
            g = server.instance._groups_db.fetch_one(group_id)
            prios.append(g.priority)

        return groups[prios.index(min(prios))]

    def insert(self, device: models.device.Device):
        """Add a device to the database

        The passed device model is updated with the new device identifier
        """
        with Session(self.engine) as session:
            session.add(device)
            session.commit()
            session.refresh(device)

    def update_key(self, mac: str, public_key: str):
        """Update the public key of the device specified by
        the given MAC address.
        """
        with Session(self.engine) as session:
            stmt = (
                update(models.device.Device)
                .values(public_key=public_key)
                .where(models.device.Device.mac_address == mac)
            )
            session.execute(stmt)
            session.commit()

    def update_metadata(self, mac_address: str, metadata: dict[str, str]):
        """Update the metadata of the given device."""
        with Session(self.engine) as session:
            stmt = (
                update(models.device.Device)
                .values(device_metadata=json.dumps(metadata))
                .where(models.device.Device.mac_address == mac_address)
            )
            session.execute(stmt)
            session.commit()

    def delete(self, identifier: int):
        """Delete the given device."""
        with Session(self.engine) as session:
            stmt = (
                delete(models.device.DeviceGroupAssignment)
                .where(models.device.DeviceGroupAssignment.device_id == identifier)
            )
            session.execute(stmt)
            stmt = (
                delete(models.permission.Permission)
                .where(models.permission.Permission.resource_id == identifier)
                .where(models.permission.Permission.resource == DEVICE_RESOURCE)
            )
            session.execute(stmt)
            stmt = (
                delete(models.device.Device)
                .where(models.device.Device.id == identifier)
            )
            session.execute(stmt)
            session.commit()
