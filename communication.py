import socket
import json
import sys
import jsonschema
import os
import pty

from threading import Thread
from enum import Enum
from datetime import datetime
from abc import abstractmethod
from typing import Optional, cast

HEADER_LENGTH = 10
REQUEST_SCHEMA = {}
with open('json_schemas/request_schema.json', 'r') as f:
    REQUEST_SCHEMA = json.loads(f.read())


class ClientType(Enum):
    USER = "user",
    DEVICE = "device"


class Client:
    def __init__(self, name: str, socket: socket.socket):
        self.name = name
        self._socket = socket

    @staticmethod
    def registration_packet(client_type: str, name: str) -> dict:
        """Creates registration packet to send to the server

        Args:
            client_type: Specifies if client is a user or a device
            name: With what name the device wants to be identified

        Returns:
            Registration request for a client in the server
        """
        registration_request = {
            'method': 'register',
            'client': {
                'group': client_type,
                'name': name
            }
        }
        jsonschema.validate(instance=registration_request,
                            schema=REQUEST_SCHEMA)
        return registration_request

    def get_server_addr(self) -> tuple[str, int]:
        """Wrapper for getting address of the server from the socket

        Returns:
            Address of the server
        """

        (ip_addr, port) = self._socket.getsockname()
        return (ip_addr, port)

    def send(self, message: dict) -> None:
        """Wrapper for message sending

        Args:
            message: To send
        """
        self._socket.send(encode_json(message))

    def receive(self) -> Optional[dict]:
        """Wrapper for message receiving

        Returns:
            Received message
        """
        return receive_message(self._socket)

    @abstractmethod
    def handle_request(self, request: dict) -> Optional[dict]:
        """Constructs reply for servers request

        Args:
            request: request from the server

        Returns:
            Constructed reply to send to the server
        """
        pass


class Device(Client):
    def __init__(self, name: str, socket: socket.socket):
        super().__init__(name, socket)
        self.metadata: dict = {}
        self.metadata_file = ''

    def update_metadata(self) -> None:
        """Collects device metadata
        As a test for now just reads prepared sample data from json file
        """

        if self.metadata_file:
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.loads(f.read())
            self.metadata['last_updated'] = str(datetime.now())
        # TODO: other methods of gathering metadata

    def handle_request(self, request: dict) -> Optional[dict]:
        if request['method'] == 'update':
            self.update_metadata()
            return {
                'method': 'metadata',
                'metadata': self.metadata
            }
        elif request['method'] == 'connect_reverse':
            print('received proxy request')
            assert request['port'] is not None
            t = Thread(target=self.connect_reverse, args=(request['port'], ))
            t.start()
        return None

    def connect_reverse(self, port: int) -> None:
        """Creates reverse shell connection with the server

        Args:
            port: At which port to connect to the server
        """
        print(f'Connecting to proxy at {port}')
        s: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.get_server_addr()[0], port))

        # open shell
        os.dup2(s.fileno(), 0)
        os.dup2(s.fileno(), 1)
        os.dup2(s.fileno(), 2)
        pty.spawn("/bin/sh")


class User(Client):
    def handle_request(self, request: dict) -> Optional[dict]:
        return super().handle_request(request)


def receive_message(client: socket.socket) -> Optional[dict]:
    """Handles message receiving

    Args:
        client: Socket from which to receive a message

    Returns:
        Received message if it was succesful
    """
    try:
        message_header: bytes = client.recv(HEADER_LENGTH)

        # connection closed
        if not message_header:
            return None

        message_length = cast(int, decode_json(message_header))
        decoded_message = cast(dict, decode_json(client.recv(message_length)))
        jsonschema.validate(instance=decoded_message, schema=REQUEST_SCHEMA)
        return decoded_message

    except Exception as e:
        # client closed connection violently
        print(f'exception receiving message: {str(e)}'),
        return None


def encode_json(to_encode: dict | str) -> bytes:
    """Encodes a dict structure to send over the tcp socket

    Args:
        to_encode: Dict to encode and send

    Returns:
        Encoded json with header
    """
    content = json.dumps(to_encode).encode('utf-8')
    return f"{len(content):<{HEADER_LENGTH}}".encode('utf-8') + content


def decode_json(to_decode: bytes) -> dict | int:
    """Decodes received json received from the tcp socket, without header

    Args:
        to_decode: Encoded json

    Returns:
        Decoded json to dict or str
    """
    decoded = json.loads(to_decode.decode('utf-8').strip())
    assert isinstance(decoded, dict) or isinstance(decoded, int)
    return decoded


def create_client(client_type: str, name: str,
                  socket: socket.socket) -> Optional[Client]:
    """Creates a new client

    Args:
        client_type: Tells if client wants to be recognized as user of device
        name: With what name the device wants to be identified
        socket: Socket with which the client is connecting to the server
        file: Path to the file containing metadata

    Returns:
        Data structure containing client info if creation was succesful

    Throws:
        AttributeError: Provided not supported client type
    """
    try:
        client_enum = getattr(ClientType, client_type)
        if client_enum == ClientType.USER:
            return User(name, socket)
        elif client_enum == ClientType.DEVICE:
            return Device(name, socket)
        else:
            return None
    except AttributeError:
        print(f'Error: {client_type} is not a valid client type')
        sys.exit(1)


def create_listening_socket(hostname: str, port: int = 0) -> socket.socket:
    """Creates listening socket

    Args:
        hostname: hostname to listen on
        port: port to listen on, defaults to ephemeral port

    Returns:
        Socket for server to listen for incoming connections
    """

    new_socket: socket.socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
    new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    new_socket.bind((hostname, port))
    new_socket.listen()
    return new_socket


def create_alert(alert_content: dict) -> dict:
    """Creates a message that client doesn't have to respond to

    Args:
        alert_content: Message that we want to send as an alert

    Returns:
        Wrapped message according to JSON schema alert structure
    """
    return {
        'method': 'alert',
        'alert': alert_content
    }