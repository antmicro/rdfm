from __future__ import annotations
import socket
import json
from enum import Enum
from datetime import datetime
from abc import abstractmethod

from typing import Optional

HEADER_LENGTH = 10

class ClientType(Enum):
    USER = "USER",
    DEVICE = "DEVICE"

class Client():
    def __init__(self, name: str, socket: socket.socket):
        self.name = name
        self.socket = socket

    @staticmethod
    def registration_packet(client_type: str, name: str) -> bytes:
        """Creates registration packet to send to the server

        Args:
            client_type: Specifies if client is a user or a device
            name: With what name the device wants to be identified

        Returns:
            Serialized json to register a client in the server
        """
        registration_request = {
            'type': client_type,
            'name': name
        }
        return encode_json(registration_request)
    
    def send(self, message: dict) -> None:
        """Wrapper for message sending
        
        Args:
            message: To send
        """
        self.socket.send(encode_json(message))

    @abstractmethod
    def handle_request(self, request: str | dict) -> str:
        """Constructs reply for servers request

        Args:
            request: request from the server

        Returns: constructed reply to send to the server
        """
        None

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
            with open (self.metadata_file, 'r') as f:
                self.metadata = json.loads(f.read())
            self.metadata['last_updated'] = str(datetime.now())
        #TODO: other methods of gathering metadata

    def handle_request(self, request: str | dict) -> str:
        if request == 'refresh':
            self.update_metadata()
            return {'metadata': self.metadata}

class User(Client):
    def proxy_request(self, device_name: str) -> str:
        """Send proxy connection request to the device

        Args:
            device_name: Name of the device that we want to connect to
        """
        return f"REQ {device_name} proxy"
    
    def device_info_request(self, device_name: str) -> str:
        """Send request for the device metadata

        Args:
            device_name: Name of the device that we want to connect to
        """
        return f"REQ {device_name} info"
    
    def device_refresh_info_request(self, device_name: str) -> str:
        """Send request to force device to upload fresh metadata

        Args:
            device_name: Name of the device that we want to connect to
        """
        return f"REQ {device_name} refresh"
    
def receive_message(client: socket.socket):
    """Handles message receiving

    Args:
        client: Socket from which to receive a message

    Returns:
        Optional[JSON]: Received message if it was succesful
    """
    try:
        message_header: bytes = client.recv(HEADER_LENGTH)

        # connection closed
        if not message_header:
            return None
        
        message_length = int(decode_json(message_header))

        return decode_json(client.recv(message_length))

    except Exception as e:
        # client closed connection violently
        print(f'exception receiving message: {str(e)}'),
        return None
    
def encode_json(to_encode: dict) -> bytes:
    """Encodes a dict structure to send over the tcp socket

    Args:
        to_encode: Dict to encode and send

    Returns:
        Encoded json with header
    """
    content = json.dumps(to_encode).encode('utf-8')
    return f"{len(content):<{HEADER_LENGTH}}".encode('utf-8') + content

def decode_json(to_decode: bytes) -> dict | str | bytearray:
    """Decodes received json received from the tcp socket, without header

    Args:
        to_decode: Encoded json
        
    Returns:
        Decoded json to dict or str
    """
    return json.loads(to_decode.decode('utf-8').strip())

def create_client(client_type: str, name: str, socket: socket.socket) -> Optional[Client]:
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
            return None
        
def create_listening_socket(hostname: str, port: int = 0) -> socket.socket:
        """Creates listening socket

        Args:
            hostname: hostname to listen on
            port: port to listen on, defaults to ephemeral port

        Returns:
            Socket for server to listen for incoming connections
        """
        new_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        new_socket.bind((hostname, port))
        new_socket.listen()
        return new_socket