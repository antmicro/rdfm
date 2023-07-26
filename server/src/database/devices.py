import sqlite3
import time
import os
import json
import datetime
from typing import Optional
from rdfm_mgmt_communication import Device
import models.device
from sqlalchemy import create_engine, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData

class DevicesDB:
    engine: Engine

    def __init__(self, filepath: str):
        self.filepath = filepath
        if not filepath.endswith('.db'):
            self.filepath = filepath + '.db'
        if not self.init_db():
            print("Database connection failed")
        else:
            print("Database connected")
        

    def init_db(self) -> bool:
        """Creates connection to device database and creates table if not exists
        
        Returns:
            Creation success
        """
        try:
            self.engine = create_engine("sqlite:///devices.db", echo=True)
            # This actually creates all the tables in the database for entities that inherit from models.device.Base
            models.device.Base.metadata.create_all(self.engine)
            return True
        except:
            print("Database init failed!")
            return False


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

    def update_timestamp(self, name: str, mac_address: str):
        """Update device's last healthcheck time in database
        """
        with Session(self.engine) as session:
            stmt = (
                update(models.device.Device)
                    .values(last_accessed=datetime.datetime.now())
                    .where(models.device.Device.name == name)
                    .where(models.device.Device.mac_address == mac_address)
            )
            session.execute(stmt)

        
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
