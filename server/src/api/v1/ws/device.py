from rdfm.ws import WebSocketException
from flask import Blueprint
import simple_websocket
import device_mgmt.loop
import device_mgmt.shell
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


@device_ws_blueprint.route('/api/v1/devices/<string:mac_address>/shell', websocket=True)
@management_read_write_api
@upgrade_to_websocket
def spawn_shell_for_manager(ws: simple_websocket.Client, mac_address: str):
    """ Manager WebSocket: Spawn a device shell

    Establish a shell connection to the target device. This WS endpoint is called by
    the manager to spawn a shell on the device and connect to it.
    """
    try:
        device_mgmt.shell.attach_manager_to_shell(ws, mac_address)
    except WebSocketException as e:
        print("Terminating management WS connection:", e.message, flush=True)
        raise


@device_ws_blueprint.route('/api/v1/devices/<string:mac_address>/shell/attach/<string:uuid>', websocket=True)
@device_api
@upgrade_to_websocket
def attach_device_shell_to_manager(ws: simple_websocket.Client, mac_address: str, uuid: str, device_token: DeviceToken):
    """ Device WebSocket: Connect to manager

    This WS endpoint is meant to be used by a device for streaming the
    contents of the shell session.
    """
    try:
        device_mgmt.shell.attach_device_to_manager(ws, mac_address, uuid)
    except WebSocketException as e:
        print("Terminating device shell WS connection:", e.message, flush=True)
        raise
