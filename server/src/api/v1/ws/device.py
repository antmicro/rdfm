from rdfm.ws import WebSocketException
from flask import Blueprint
import simple_websocket
import device_mgmt.loop
from api.v1.middleware import upgrade_to_websocket, device_api, DeviceToken, management_read_write_api
from simple_websocket import Server, ConnectionClosed
from flask import request, Response


device_ws_blueprint: Blueprint = Blueprint("rdfm-server-device-ws", __name__)


@device_ws_blueprint.route('/api/v1/devices/ws', websocket=True)
@device_api
@upgrade_to_websocket
def device_management_ws(ws: simple_websocket.Client, device_token: DeviceToken):
    """ Device WebSocket: Device management

    This is the device management WebSocket endpoint. All devices are expected
    to establish a connection to this WebSocket.
    """
    try:
        device_mgmt.loop.start_device_event_loop(ws, device_token)
    except WebSocketException as e:
        print("Terminating device WS connection:", e.message, flush=True)
        raise
