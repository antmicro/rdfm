from typing import List, Optional
import models.device_update
from sqlalchemy import select, update, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class DeviceUpdatesDB:
    """Wrapper class for storing device update progress"""

    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db

    def fetch_all(self) -> List[models.device_update.DeviceUpdate]:
        """Fetches all device updates from the database"""
        with Session(self.engine) as session:
            stmt = select(models.device_update.DeviceUpdate)
            updates = session.scalars(stmt)
            if updates is None:
                return []
            return [x for x in updates]

    def insert(self, update: models.device_update.DeviceUpdate):
        """Add a device update to the database"""
        with Session(self.engine) as session:
            session.add(update)
            session.commit()
            session.refresh(update)
            return update.id

    def get_version(self, mac_address: str) -> str:
        """Fetch the software version that a specified device is being updated to.
        """
        with Session(self.engine) as session:
            return session.scalar(
                select(models.device_update.DeviceUpdate.version)
                .where(models.device_update.DeviceUpdate.mac_address == mac_address)
            )

    def update_progress(self, mac_address: str, progress: int):
        """Update the progress of a specified device.
        """
        with Session(self.engine) as session:
            stmt = (
                update(models.device_update.DeviceUpdate)
                .values(progress=progress)
                .where(models.device_update.DeviceUpdate.mac_address == mac_address)
            )
            session.execute(stmt)
            session.commit()

    def delete(self, mac_address: str):
        """Removes a completed device update.
        """
        with Session(self.engine) as session:
            stmt = (
                delete(models.device_update.DeviceUpdate)
                .where(models.device_update.DeviceUpdate.mac_address == mac_address)
            )
            session.execute(stmt)
            session.commit()
