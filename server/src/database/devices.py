import sqlite3
import time
import os
import json
from typing import Optional
from rdfm_mgmt_communication import Device

class DevicesDB:
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
        self._db_con: sqlite3.Connection = sqlite3.connect(
            self.filepath, check_same_thread=False
        )
        cur = self._db_con.cursor()
        cur.execute(
            f"""CREATE TABLE if not exists
            devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_access INTEGER NOT NULL,
                name TEXT NOT NULL,
                mac_address TEXT NOT NULL,
                capabilities TEXT NOT NULL,  --json dump of capabilities
                metadata TEXT NOT NULL       --json dump of collected metadata
            )
            """
        )
        res = cur.execute(
            f"""SELECT name FROM sqlite_master
            WHERE name='devices'"""
        )
        return res is not None


    def get_device(self, name: str, mac_address: str) -> Optional[Device]:
        """Gets device from database
        
        Returns:
            Device object without socket recreated from database row
        """
        cur = self._db_con.cursor()
        cur.execute(
            f"""SELECT * from devices
            WHERE name = ? AND mac_address = ?""",
            (name, mac_address)
        )
        row = cur.fetchone()
        if row:
            print(row)
            (dev_id, timestamp, name, mac_addr,
             capabilities_dump, metadata_dump) = row
            device = Device(name, None, mac_addr,
                            json.loads(capabilities_dump))
            device.metadata = json.loads(metadata_dump)
            
            return device
        return None

    def update_timestamp(self, name: str, mac_address: str):
        """Update device's last healthcheck time in database
        """
        cur = self._db_con.cursor()
        cur.execute(
            f"""UPDATE devices
            WHERE name = ? AND mac_address = ?""",
            (name, mac_address)
        )
        
    def insert_device(self, device: Device):
        """Add device to database
        """
        cur = self._db_con.cursor()
        cur.execute(
            f"""INSERT INTO devices
            (name, mac_address, last_access, capabilities, metadata)
            values (?, ?, ?, ?, ?);""",
            (device.name, device.mac_address, int(time.time()),
             json.dumps(device.capabilities), json.dumps(device.metadata))
        )
        self._db_con.commit()

    def __del__(self):
        self._db_con.close()