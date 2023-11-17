import time
from device_mgmt.models.remote_device import RemoteDevice
import simple_websocket
from auth.device import DeviceToken
from rdfm.ws import (RDFM_WS_DUPLICATE_CONNECTION,
                     WebSocketException)
import server


def start_device_event_loop(ws: simple_websocket.Client, device_token: DeviceToken):
    """ Start the main event loop for a device websocket
    """
    device = RemoteDevice(ws, device_token)

    # Save the WS connection
    previous = server.instance.remote_devices.get(device.token.device_id)
    if previous is not None:
        # This is a workaround for an upstream library issue
        # When a ping fails, and we don't receive a response
        # from the device, simple_websocket does not signal
        # threads that called receive() with no timeout
        # to close. When this issue is resolved, this can be
        # removed entirely.
        # See: https://github.com/miguelgrinberg/simple-websocket/pull/33
        if not previous.ws.connected:
            print("Detected stale device connection, forcing a close", flush=True)
            previous.ws.event.set()
            time.sleep(2.0)
        else:
            raise WebSocketException("duplicate connections not allowed", RDFM_WS_DUPLICATE_CONNECTION)

    server.instance.remote_devices.add(device)

    # Enter the event loop
    # On exit, remove the device from tracked ones
    try:
        device.event_loop()
    finally:
        server.instance.remote_devices.remove(device)
