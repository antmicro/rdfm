import sqlite3
import time
import os
import json
import datetime
from typing import Optional, List
from rdfm_mgmt_communication import Device
import models.device
from sqlalchemy import create_engine, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData

class DevicesDB:
    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db
        

    def get_device(self, name: str, mac_address: str) -> Optional[Device]:
        """Gets device from database
        
        Returns:
            Device object without socket recreated from database row
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    select(models.device.Device)
                        .where(models.device.Device.name == name)
                        .where(models.device.Device.mac_address == mac_address)
                )
                dev: models.device.Device = session.scalar(stmt)
                if dev is None:
                    return None

                server_device = Device(dev.name,
                                       None,
                                       dev.mac_address, 
                                       json.loads(dev.capabilities))
                server_device.metadata = json.loads(dev.device_metadata)
                return server_device
        except Exception as e:
            print("Device fetch failed!", repr(e))
            return None

    def get_device_data(self, mac_address: str) -> Optional[models.device.Device]:
        with Session(self.engine) as session:
            stmt = (
                select(models.device.Device)
                    .where(models.device.Device.mac_address == mac_address)
            )
            return session.scalar(stmt)


    def update_timestamp(self, mac_address: str, timestamp: datetime.datetime):
        """Update device's last healthcheck time in database
        """
        with Session(self.engine) as session:
            stmt = (
                update(models.device.Device)
                    .values(last_access=timestamp)
                    .where(models.device.Device.mac_address == mac_address)
            )
            session.execute(stmt)
            session.commit()


    def insert_device(self, device: Device):
        """Add device to database
        """
        with Session(self.engine) as session:
            db_device = models.device.Device()
            db_device.name = device.name
            db_device.mac_address = device.mac_address
            db_device.capabilities = json.dumps(device.capabilities)
            db_device.device_metadata = json.dumps(device.metadata)

            session.add(db_device)
            session.commit()


    def fetch_all(self) -> List[models.device.Device]:
        """ Fetch a list of all devices found in the database
        """
        with Session(self.engine) as session:
            return session.scalars(
                select(models.device.Device)
            ).all()


    def fetch_one(self, identifier: int) -> models.device.Device:
        """ Fetch data of the device with a given identifier
        """
        with Session(self.engine) as session:
            return session.scalar(
                select(models.device.Device)
                .where(models.device.Device.id == identifier)
            )


    def insert(self, device: models.device.Device):
        """ Add a device to the database

        The passed device model is updated with the new device identifier
        """
        with Session(self.engine) as session:
            session.add(device)
            session.commit()
            session.refresh(device)


    def update_key(self, mac: str, public_key: str):
        """ Update the public key of the device specified by
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
        """ Update the metadata of the given device.
        """
        with Session(self.engine) as session:
            stmt = (
                update(models.device.Device)
                .values(device_metadata=json.dumps(metadata))
                .where(models.device.Device.mac_address == mac_address)
            )
            session.execute(stmt)
            session.commit()
