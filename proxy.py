import socket
import select
import sys
from typing import Final

from communication import *

PROXY_BUFFER_SIZE: Final = 4096

class Proxy:
    def __init__(self, hostname: str, user: User, device: Device):
        """Creates a proxy connection between user and device

        Here a new server listening socket is created.
        The device receives a message containing the new port and connects with reverse shell to it.
        After the device connects user receives message about the new port to connect to.
        If a client disconnects the proxy should send disconnect message to
        the client it was connected by proxy with.
        Also proxy socket should close, without disrupting other existing connections
        and server stability.

        Args:
            hostname: IP addr of the server
            user: User that required proxy connection
            device: Device that the user requested to connect to
        """
        self.device: Device = device
        self.user: User = user

        self.proxy_device_socket: Optional[socket.socket] = None
        self.proxy_user_socket: Optional[socket.socket] = None

        # creating new server listening socket
        self.proxy_listen_socket: socket.socket = create_listening_socket(hostname)
        self.sockets: list[socket.socket] = [self.proxy_listen_socket]

        self._port: int = self.proxy_listen_socket.getsockname()[1]
        print(f'Opened proxy socket at {self._port}',
              f'(user: {user.name}, device: {device.name})')

    def send_connection_request(self) -> None:
        """Send connection request and new port to the device"""
        self.device.send({
            'request': 'proxy',
            'port': self._port
        })

    def run(self) -> None:
        """Main proxy loop for forwarding messages between user and device.
        Started with sending a connection request to the device so it connects
        with a new socket"""
        self.send_connection_request()
        while True:
            read_sockets, _, exception_sockets = select.select(self.sockets, [], self.sockets)
            for notified_socket in read_sockets:
                # someone new connected to the proxy
                if notified_socket == self.proxy_listen_socket:
                    # assume that device should connect first
                    if not self.proxy_device_socket:
                        self.proxy_device_socket, proxy_device_address = self.proxy_listen_socket.accept()
                        print(f"Device connected to proxy: {proxy_device_address}")
                    
                        device_message: bytes = self.proxy_device_socket.recv(PROXY_BUFFER_SIZE)
                        # disconnected immediately
                        if not device_message:
                            continue

                        self.sockets.append(self.proxy_device_socket)
                        # send connection invitation to the user
                        self.user.send({'message': f'connect to shell at {self._port}'})
                    # user connected
                    else:
                        self.proxy_user_socket, proxy_user_address = self.proxy_listen_socket.accept()
                        print(f"User connected to proxy: {proxy_user_address}")
                        self.proxy_user_socket.send(device_message)
                        self.sockets.append(self.proxy_user_socket)

                elif notified_socket in [self.proxy_device_socket, self.proxy_user_socket]:
                    message: bytes = notified_socket.recv(PROXY_BUFFER_SIZE)
                    # client disconnected from proxy connection - close it and exit thread
                    if not message:
                        print(f'Closed proxy socket at {self._port}',
                              f'(user: {self.user.name}, device: {self.device.name})')
                        sys.exit()
                    
                    # device -> user
                    if notified_socket == self.proxy_device_socket:
                        assert self.proxy_user_socket is not None
                        self.proxy_user_socket.send(message)

                    # user -> device
                    elif notified_socket == self.proxy_user_socket:
                        assert self.proxy_device_socket is not None
                        self.proxy_device_socket.send(message)

            for notified_socket in exception_sockets:
                self.sockets.remove(notified_socket)
                print(f"Proxy connection with {self.device.name} ended");
                # send empty message to disconnect new sockets
                if notified_socket == self.proxy_device_socket and self.proxy_user_socket:
                    assert self.proxy_user_socket is not None
                    self.proxy_user_socket.send(b'');
                else:
                    assert self.proxy_device_socket is not None
                    self.proxy_device_socket.send(b'')
                sys.exit()