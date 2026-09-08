import time
from device_mgmt.models.remote_device import RemoteDevice
import simple_websocket
from auth.device import DeviceToken
from rdfm.ws import RDFM_WS_DUPLICATE_CONNECTION, RDFM_WS_UNAUTHORIZED, WebSocketException
import server


def start_device_event_loop(
    ws: simple_websocket.Client, device_token: DeviceToken
):
    """Start the main event loop for a device websocket"""

    # Check if device trying to connect is present in database
    # This is simpler than maintaining a list of revoked tokens
    device_db_entry = server.instance._devices_db.get_device_data(device_token.device_id)
    if device_db_entry is None:
        raise WebSocketException("device not registered", RDFM_WS_UNAUTHORIZED)
    device = RemoteDevice(ws, device_token)

    # Save the WS connection
    previous = server.instance.remote_devices.get(device.token.device_id)
    if previous is not None:
        raise WebSocketException("duplicate connections not allowed", RDFM_WS_DUPLICATE_CONNECTION)

    server.instance.remote_devices.add(device)

    # Enter the event loop
    # On exit, remove the device from tracked ones
    try:
        device.event_loop()
    finally:
        server.instance.remote_devices.remove(device)
