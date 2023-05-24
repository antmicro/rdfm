from __future__ import annotations
import socket
import json
from enum import Enum

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

class Device(Client):
    pass

class User(Client):
    # for incoming proxy CI tests
    def proxy_request(self, device_name: str, message: str="") -> str:
        """Send proxy connection request to the device specified by name

        Args:
            device_name: Name of the device that we want to connect to
            message: Message that we want to pass to the device
        """
        return f"REQ {device_name} {message}"
    
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

def register_client(client_type: str, name: str, socket: socket.socket) -> Optional[Client]:
        """Register a new client connection

        Args:
            client_type: Tells if client wants to be recognized as user of device
            name: With what name the device wants to be identified
            socket: Socket with which the client is connecting to the server

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