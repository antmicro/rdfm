from typing import Optional
import typing
from rdfm_mgmt_communication import decode_json
from request_models import Request
from simple_websocket.errors import ConnectionClosed, ConnectionError
import simple_websocket


""" Standard error codes as defined in RFC 6455
"""
WS_UNSUPPORTED_DATA: int = 1003


""" Custom RDFM-specific error codes

These must fall in the range 4000-4999
"""
RDFM_WS_UNAUTHORIZED: int = 4000
RDFM_WS_INVALID_REQUEST: int = 4001
RDFM_WS_DUPLICATE_CONNECTION: int = 4002
RDFM_WS_MISSING_CAPABILITIES: int = 4003


""" Capabilities required to perform a certain management request
"""
__required_capabilities_by_method_name: dict[str, list[str]] = {
    'device_hello': [],
    'shell_attach': ['shell'],
    'alert': [],
    'action_exec': ['action'],
    'action_list_query': ['action'],
}


def can_handle_request(capabilities: dict[str, bool], request_method: str) -> bool:
    """ Checks if a device has the required capabilities for the specified method

    Args:
        capabilities - dictionary of device capabilities
        request_method - `method` field of the request, ex. "proxy"

    Returns:
        True if device can handle given method
    """
    return all(c in capabilities and capabilities[c]
               for c in __required_capabilities_by_method_name[request_method])


class WebSocketException(Exception):
    """ Common exception class for errors during device
        websocket connection.

    All WebSocket routes catch this exception and close the WS connection
    with the specified status code and message.
    The status code is a WebSocket status code, not HTTP!
    """
    status_code: int
    message: str

    def __init__(self, message: str, status_code: int) -> None:
        """ Initialize the exception

        Args:
            message: message explaining the condition. This value
                     is returned to the client as part of the WS
                     termination message
            status_code: WebSocket status code to return in the WS
                         termination message
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def receive_message(ws: simple_websocket.Client, timeout: Optional[float] = None) -> Request:
    """ Receive an RDFM message from a WebSocket and decode it

    A message is a simple JSON struct defining the method to call.
    We use text-mode encoding for this, and the protocol does not
    currently use any binary-mode messages.

    Args:
        ws: a connected WebSocket to receive a message from
        timeout: optional message receive timeout (in seconds)

    Throws:
        WebSocketException: an invalid message was received or
                            the read timed out
    """
    try:
        data = ws.receive(timeout=timeout)
        if isinstance(data, bytes):
            raise WebSocketException("device socket requires text-mode encoding",
                                     WS_UNSUPPORTED_DATA)
        if data is None:
            raise WebSocketException("websocket read timed out", RDFM_WS_INVALID_REQUEST)
    except ConnectionClosed as e:
        message = "device disconnected"
        if e.message is not None and len(e.message) > 0:
            message += f": {e.message}"
        raise WebSocketException(message, e.reason)

    try:
        return decode_json(data.encode())
    except Exception as e:
        print("Device WS: Malformed message received, exception during decoding:", e, flush=True)
        raise WebSocketException("invalid request", RDFM_WS_INVALID_REQUEST)


def send_message(ws: simple_websocket.Client, request: Request):
    """ Send an RDFM message to a WebSocket

    Sends the specified RDFM message over the connected WebSocket.

    Args:
        ws: a connected WebSocket to send the message to
        request: RDFM message to send

    Throws:
        WebSocketException: a connection error has occured
    """
    try:
        ws.send(request.json())
    except (ConnectionClosed, ConnectionError):
        raise WebSocketException("device disconnected", RDFM_WS_INVALID_REQUEST)
    except Exception as e:
        print("Device WS: Sending message failed:", e, flush=True)
        raise WebSocketException("invalid request", RDFM_WS_INVALID_REQUEST)
