import threading
import sys
import json
from typing import Optional
from request_models import (
    Request,
    CapabilityReport,
    Alert,
    Action,
    ActionExec,
    ActionExecResult,
    ActionExecGeneratedFile,
    ActionExecControl,
    ActionListUpdate,
    FsFileDownloadReply,
    FsFileProbeReply,
    UpdateProgress,
    UpdateFailure,
    UpdateVersion,
)

import simple_websocket
from auth.token import DeviceToken
import rdfm.ws
from rdfm.ws import (
    RDFM_WS_INVALID_REQUEST,
    RDFM_WS_MISSING_CAPABILITIES,
    WebSocketException,
)
from rdfm.schema.v1.updates import META_SOFT_VER
import device_mgmt.action
import server

import logging

log = logging.getLogger(__name__)


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
        self.capabilities_updated = threading.Event()
        self.actions_updated = threading.Event()
        self.update_version = None

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
                "device does not support the required method: "
                f"{request.method}",
                RDFM_WS_MISSING_CAPABILITIES,
            )

        rdfm.ws.send_message(self.ws, request)

    def __handle_device_message(self, request: Request):
        """Handle an incoming device request"""
        if isinstance(request, CapabilityReport):
            log.info(
                "Capability update for %s reporting capabilities: %s",
                self.token.device_id,
                request.capabilities,
            )
            self.capabilities = request.capabilities
            server.instance._devices_db.update_capabilities(
                self.token.device_id, request.capabilities
            )
            self.capabilities_updated.set()
        elif isinstance(request, ActionExecResult):
            log.info(
                "Action execution result for %s: execution_id=%s status_code=%s output=%s",
                self.token.device_id,
                request.execution_id,
                request.status_code,
                request.output,
            )
            device_mgmt.action.execute_action_result(
                request.execution_id,
                request.status_code,
                request.output,
            )
        elif isinstance(request, ActionExecGeneratedFile):
            log.info(
                "Generated file from action execution for %s: execution_id=%s filename=%s len=%s",
                self.token.device_id,
                request.execution_id,
                request.filename,
                len(request.content),
            )
            device_mgmt.action.execute_action_generated_file(
                request.execution_id,
                request.filename,
                request.content,
            )
        elif isinstance(request, ActionExecControl):
            log.info(
                "Action execution control for %s: execution_id=%s status=%s",
                self.token.device_id,
                request.execution_id,
                request.status,
            )
            device_mgmt.action.execute_action_control(request.execution_id, request.status)
        elif isinstance(request, ActionListUpdate):
            log.info(
                "Actions update for %s reporting actions: %s",
                self.token.device_id,
                request.actions,
            )
            self.actions = {x.action_id: x for x in request.actions}
            self.actions_updated.set()
        elif isinstance(request, FsFileDownloadReply):
            log.info(
                "Filesystem download reply for %s: id=%s",
                self.token.device_id,
                request.id,
            )
            operation = server.instance.filesystem_operations.get(request.id)
            if operation:
                operation.response = request
                operation.completed.set()
            else:
                raise WebSocketException(
                    "invalid filesystem response", RDFM_WS_INVALID_REQUEST
                )
        elif isinstance(request, FsFileProbeReply):
            log.info(
                "Filesystem probe reply for %s: id=%s",
                self.token.device_id,
                request.id,
            )
            operation = server.instance.filesystem_operations.get(request.id)
            if operation:
                operation.response = request
                operation.completed.set()
            else:
                raise WebSocketException(
                    "invalid filesystem response", RDFM_WS_INVALID_REQUEST
                )
        elif isinstance(request, UpdateProgress):
            if not self.update_version:
                self.update_version = server.instance._device_updates_db.get_version(
                    self.token.device_id
                )
            if request.progress == 100:
                self.update_version = None
                server.instance._device_updates_db.delete(self.token.device_id)
                log.info(
                    "Device %s update complete", self.token.device_id
                )
            else:
                server.instance._device_updates_db.update_progress(
                    self.token.device_id,
                    request.progress
                )
                log.info(
                    "Device %s update in progress: %s%%",
                    self.token.device_id,
                    request.progress
                )
        elif isinstance(request, UpdateFailure):
            self.update_version = None
            server.instance._device_updates_db.delete(self.token.device_id)
            log.info(
                f"Device {self.token.device_id} update failed",
            )
        elif isinstance(request, UpdateVersion):
            device = server.instance._devices_db.get_device_data(self.token.device_id)
            metadata = json.loads(device.device_metadata)
            metadata[META_SOFT_VER] = request.version
            server.instance._devices_db.update_metadata(self.token.device_id, metadata)

        else:
            log.warning("Unknown request: %s", request)
            raise WebSocketException(
                "invalid request", RDFM_WS_INVALID_REQUEST
            )

    def event_loop(self):
        """Main device event loop

        This reads incoming messages from the device
        """
        log.info(
            "Device WS: Device %s connected to management WS",
            self.token.device_id,
        )
        self.send_message(
            Alert(
                alert={
                    "message": "connected",
                }
            )
        )

        thread = threading.Thread(
            target=device_mgmt.action.send_action_queue,
            args=(self.token.device_id, )
        )
        thread.start()

        while True:
            self.__handle_device_message(self.receive_message())
