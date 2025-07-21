import threading
from typing import Optional
from request_models import (
    Request,
    CapabilityReport,
    Alert,
    Action,
    ActionExecResult,
    ActionExecControl,
    ActionListUpdate,
)

import simple_websocket
from auth.token import DeviceToken
import rdfm.ws
from rdfm.ws import (
    RDFM_WS_INVALID_REQUEST,
    RDFM_WS_MISSING_CAPABILITIES,
    WebSocketException,
)
import device_mgmt.action
import server


class RemoteDevice:
    """Represents a remote management connection to a device

    This can be used to send and receive messages from a device registered
    on the RDFM server that has connected to the device WebSocket.
    """

    ws: simple_websocket.Client
    token: DeviceToken
    capabilities: dict[str, bool]
    actions: dict[str, Action]
    actions_updated: threading.Event

    def __init__(
        self, ws: simple_websocket.Client, token: DeviceToken
    ) -> None:
        self.ws = ws
        self.token = token
        self.capabilities = {}
        self.actions = {}
        self.actions_updated = threading.Event()

    def receive_message(self, timeout: Optional[float] = None) -> Request:
        """Receive a message from the device and decode it

        A message is a simple JSON struct defining the method to call.
        We use text-mode encoding for this, and the protocol does not
        currently use any binary-mode messages.
        """
        return rdfm.ws.receive_message(self.ws, timeout)

    def send_message(self, request: Request):
        """Send a message to the device

        Sends the specified message to the device over the connected WebSocket.
        If the device does not support given request method, raises
        `WebSocketException`.
        """
        if not rdfm.ws.can_handle_request(self.capabilities, request.method):
            raise WebSocketException(
                f"device does not support the required method: \
                {request.method}",
                RDFM_WS_MISSING_CAPABILITIES,
            )

        rdfm.ws.send_message(self.ws, request)

    def __handle_device_message(self, request: Request):
        """Handle an incoming device request"""
        if isinstance(request, CapabilityReport):
            print(
                "Capability update for",
                self.token.device_id,
                "reporting capabilities:",
                request.capabilities,
                flush=True,
            )
            self.capabilities = request.capabilities
            server.instance._devices_db.update_capabilities(
                self.token.device_id, request.capabilities
            )
        elif isinstance(request, ActionExecResult):
            print(
                "Action execution result for",
                self.token.device_id,
                request.execution_id,
                request.status_code,
                request.output,
                flush=True,
            )
            device_mgmt.action.execute_action_result(
                request.execution_id,
                request.status_code,
                request.output,
            )
        elif isinstance(request, ActionExecControl):
            print(
                "Action execution control for",
                self.token.device_id,
                request.execution_id,
                request.status,
                flush=True,
            )
            device_mgmt.action.execute_action_control(request.execution_id, request.status)
        elif isinstance(request, ActionListUpdate):
            print(
                "Actions update for",
                self.token.device_id,
                "reporting actions:",
                request.actions,
                flush=True,
            )
            self.actions = {x.action_id: x for x in request.actions}
            self.actions_updated.set()
        else:
            print("Unknown request:", request, flush=True)
            raise WebSocketException(
                "invalid request", RDFM_WS_INVALID_REQUEST
            )

    def event_loop(self):
        """Main device event loop

        This reads incoming messages from the device
        """
        print(
            "Device WS: Device",
            self.token.device_id,
            "connected to management WS",
            flush=True,
        )
        self.send_message(
            Alert(
                alert={
                    "message": "connected",
                }
            )
        )

        while True:
            self.__handle_device_message(self.receive_message())
