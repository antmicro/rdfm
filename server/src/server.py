from typing import Optional
from database.devices import DevicesDB
from database.packages import PackagesDB
from database.groups import GroupsDB
from database.registrations import RegistrationsDB
from database.logs import LogsDB
import database.db
import configuration
from device_mgmt.containers import RemoteDevices, ShellSessions
import datetime
from models.device import Device
from database.permissions import PermissionsDB


class Server:
    def __init__(self, config: configuration.ServerConfig):
        self.db = database.db.create(config.db_conn)
        self._devices_db: DevicesDB = DevicesDB(self.db)
        self._packages_db: PackagesDB = PackagesDB(self.db)
        self._groups_db: GroupsDB = GroupsDB(self.db)
        self._registrations_db: RegistrationsDB = RegistrationsDB(self.db)
        self._logs_db: LogsDB = LogsDB(self.db)
        self.remote_devices = RemoteDevices()
        self.shell_sessions = ShellSessions()
        self._permissions_db = PermissionsDB(self.db)

    def create_mock_data(self):
        """Creates mock data

        Fills the database with mock data to be used for testing purposes
        This does not check if the data was previously inserted, it is
        assumed that for tests a clean database is always used.
        """
        print("WARNING: Creating mock data in the database")
        print("WARNING: Do not use in production!")

        def make_dummy(mac: str) -> Device:
            return Device(
                name=mac,
                mac_address=mac,
                last_access=datetime.datetime.utcnow(),
                capabilities="{}",
                device_metadata="{}",
                public_key=None,
            )

        # Create dummy devices
        self._devices_db.insert(make_dummy("00:00:00:00:00:00"))
        self._devices_db.insert(make_dummy("11:11:11:11:11:11"))
        self._devices_db.insert(make_dummy("22:22:22:22:22:22"))


""" Global instance of the RDFM server
"""
instance: Optional[Server] = None
