from typing import Optional
from device_mgmt.models.remote_device import RemoteDevice


class RemoteDevices():
    """ Container for tracking devices connected to the management WebSocket
    """
    _remote_devices: dict[str, RemoteDevice] = {}


    def add(self, device: RemoteDevice):
        """ Add a new device to the tracked devices
        """
        self._remote_devices[device.token.device_id] = device


    def remove(self, device: RemoteDevice):
        """ Remove a device from tracked devices
        """
        self._remote_devices.pop(device.token.device_id)


    def get(self, mac_address: str) -> Optional[RemoteDevice]:
        """ Get a device connection by MAC address
        """
        return self._remote_devices.get(mac_address, None)

