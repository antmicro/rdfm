import socket
import json
import sys
import ssl
from request_models import *

from typing import Optional, cast

HEADER_LENGTH = 10

class Client:
    def __init__(self, name: str, socket: Optional[socket.socket]):
        self.name = name
        self._socket = socket

    def get_server_addr(self) -> tuple[str, int]:
        """Wrapper for getting address of the server from the socket

        Returns:
            Address of the server
        """

        (ip_addr, port) = self._socket.getsockname()
        return (ip_addr, port)

    def send(self, message: Request) -> None:
        """Wrapper for message sending

        Args:
            message: To send
        """
        self._socket.send(encode_json(message))

    def receive(self) -> Optional[Request]:
        """Wrapper for receiving a message that can contain a file part

        Returns:
            Received message
        """
        return receive(self._socket)
    
    def set_socket(self, s: socket.socket):
        """Set client socket to a new one

        Args:
            s: New socket
        """
        self._socket = s


class Device(Client):
    required_capabilities: dict[str, list[str]] = {
        'download': [ 'file_transfer' ],
        'upload': [ 'file_transfer' ],
        'proxy':[ 'shell_connect' ],
        'info': [],
        'update': [],
        'capabilities': []
    }

    def __init__(self, name: str, socket: Optional[socket.socket],
                 mac_address: str, capabilities: dict):
        super().__init__(name, socket)
        self.mac_address = mac_address
        # what interactions are available
        self.capabilities: dict[str, bool] = {
            'shell_connect': False,
            'file_transfer': False,
            'exec_cmds': False,
        }
        for k, v in capabilities.items():
            self.capabilities[k] = v

        # RO data, like sensors data, cpu usage, coords, etc.
        self.metadata: dict = {}

    def can_handle_request(self, request_method: str) -> bool:
        """Checks if device has capabilities to perform request,
        
        Args:
            request_method - `method` field of the request, ex. "proxy"

        Returns:
            Device can handle request
        """
        return all([(c in self.capabilities and self.capabilities[c])
                    for c in Device.required_capabilities[request_method]])
    
    def set_socket(self, s: socket.socket) -> None:
        """Set device client's socket to a new one
        
        Args:
            s: New socket
        """
        self._socket = s

class User(Client):
    def __init__(self, name: str, socket: socket.socket):
        super().__init__(name, socket)

    def prompt(self, message: str) -> None:
        """Prints prompt with message"""
        print('\r', message, end=f'\n{self.name} > ')


class FileTransfer():
    def __init__(self, receiver: Client, sender: Optional[Client],
                 file_path: str):
        self.receiver: Client = receiver
        self.sender: Optional[Client] = sender
        self.file_path: str = file_path


def receive(client: socket.socket) -> Optional[Request]:
    """Handles message receiving

    Args:
        client: Socket from which to receive a message

    Returns:
        Received message if it was succesful

    Throws:
        ValueError: Received message is not a valid request
    """
    try:
        message_header: bytes = client.recv(HEADER_LENGTH)

        # connection closed
        if not message_header:
            return None

        message_length = cast(int, decode_json(message_header))
        message = client.recv(message_length)
        remaining_bytes = message_length - len(message)
        while remaining_bytes > 0:
            message += client.recv(message_length)
            remaining_bytes -= len(message)
        decoded_message = decode_json(message)

        return decoded_message

    except Exception as e:
        # client closed connection violently
        print(f'Exception receiving message: {str(e)}'),
        return None


def encode_json(to_encode: Request) -> bytes:
    """Encodes a dict structure to send over the tcp socket

    Args:
        to_encode: Dict to encode and send

    Returns:
        Encoded json with header
    """
    content = to_encode.json().encode('utf-8')
    return f"{len(content):<{HEADER_LENGTH}}".encode('utf-8') + content


def decode_json(to_decode: bytes) -> Request | int:
    """Decodes json received from the tcp socket, without header

    Args:
        to_decode: Encoded json

    Returns:
        Decoded json to request or int (header with msg length)
    """
    decoded = to_decode.decode('utf-8').strip()
    if decoded.isnumeric():
        return int(decoded)
    else:
        decoded = Container.model_validate({
            'data': json.loads(to_decode)
        }).data

        return decoded


def create_client(client_group: ClientGroups, name: str,
                  socket: socket.socket,
                  capabilities: Optional[dict]) -> Optional[Client]:
    """Creates a new client

    Args:
        client_group: Tells if client wants to be recognized as user of device
        name: With what name the device wants to be identified
        socket: Socket with which the client is connecting to the server
        file: Path to the file containing metadata

    Returns:
        Data structure containing client info if creation was succesful

    Throws:
        AttributeError: Provided not supported client type
    """
    try:
        client_enum = getattr(ClientGroups, client_group)
        if client_enum == ClientGroups.USER:
            return User(name, socket)
        elif client_enum == ClientGroups.DEVICE:
            assert capabilities is not None
            return Device(name, socket, capabilities)
        else:
            return None
    except AttributeError:
        print(f'Error: {client_group} is not a valid client type')
        sys.exit(1)


def create_listening_socket(hostname: str, port: int = 0,
                            encrypted: bool = False,
                            crt: str = "", key: str = "") -> socket.socket:
    """Creates listening socket

    Args:
        hostname: hostname to listen on
        port: port to listen on, defaults to ephemeral port
        encrypted: whether connection should use SSL
        crt: server's crt path
        key: path to server's crt key

    Returns:
        Socket for server to listen for incoming connections
    """

    new_socket: socket.socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
    new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if encrypted:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(crt, key)
        new_socket = context.wrap_socket(new_socket, server_side=True)

    new_socket.bind((hostname, port))
    new_socket.listen()
    return new_socket
