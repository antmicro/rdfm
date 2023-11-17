from uuid import UUID, uuid4
import simple_websocket
import threading


class ReverseShell():
    """ Represents an active shell session

    This contains information about an active shell session tracked
    by the server. Each session is identified by a MAC:UUID pair.
    The UUID allows us to handle multiple sessions to the same device.

    The session is initiated by a manager requesting a shell on the
    device. The device then connects and sends/receives shell data
    to the saved manager WebSocket.
    """
    manager_socket: simple_websocket.Client
    device_connection_closed: threading.Event
    device_connected: threading.Event
    uuid: UUID
    mac_addr: str


    def __init__(self, ws: simple_websocket.Client, mac: str) -> None:
        """ Create a shell session

        Args:
            ws: manager WebSocket
            mac: MAC address of the target device
        """
        self.manager_socket = ws
        self.device_connection_closed = threading.Event()
        self.device_connected = threading.Event()
        self.uuid = uuid4()
        self.mac_addr = mac
