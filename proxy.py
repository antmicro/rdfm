from __future__ import annotations
import socket
import select
import sys

from communication import *

class Proxy():
    def __init__(self, hostname: str, user: User, device: Device):
        """Creates a proxy connection between user and device

        Here a new server listening socket is created.
        The device receives a message containing the new port and connects with reverse shell to it.
        After the device connects user receives message about the new port to connect to.
        If 

        Args:
            hostname: IP addr of the server
            user: User that required proxy connection
            device: Device that the user specified to connect to
        """
        self.device = device
        self.user = user

        self.new_device_socket = None
        self.new_user_socket = None

        # creating new server listening socket
        self.proxy_socket: socket.socket = create_listening_socket(hostname)
        print(self.proxy_socket)
        self.sockets: list[socket.socket] = [self.proxy_socket]

        self._port: int = self.proxy_socket.getsockname()[1]
        print(f'Opened proxy socket at {self._port} (user: {user.name}, device: {device.name})')

    def send_connection_request(self):
        """Send connection request and new port to the device"""
        self.device.send({
            'request': 'proxy',
            'port': self._port
        })

    def run(self):
        """Main proxy loop for forwarding messages between user and device.
        Started with sending a connection request to the device so it connects
        with a new socket"""
        self.send_connection_request()
        while True:
            read_sockets, _, exception_sockets = select.select(self.sockets, [], self.sockets)
            for notified_socket in read_sockets:
                # someone new connected to the proxy
                if notified_socket == self.proxy_socket:
                    # assume that device should connect first
                    if not self.new_device_socket:
                        self.new_device_socket, new_device_address = self.proxy_socket.accept()
                        print(f"Device connected to proxy: {new_device_address}")
                    
                        device_message: bytes = self.new_device_socket.recv(4096)
                        # disconnected immediately
                        if not device_message:
                            continue

                        self.sockets.append(self.new_device_socket)
                        # send connection invitation to the user
                        self.user.send({'message': f'connect to shell at {self._port}'})
                    # user connected
                    else:
                        self.new_user_socket, new_user_address = self.proxy_socket.accept()
                        print(f"User connected to proxy: {new_user_address}")
                        self.new_user_socket.send(device_message)
                        self.sockets.append(self.new_user_socket)

                elif notified_socket in [self.new_device_socket, self.new_user_socket]:
                    message = notified_socket.recv(4096)
                    # client disconnected from proxy connection - close it and exit thread
                    if not message:
                        print(f'Closed proxy socket at {self._port}',
                              f'(user: {self.user.name}, device: {self.device.name})')
                        sys.exit()
                    
                    # device -> user
                    if notified_socket == self.new_device_socket:
                        self.new_user_socket.send(message)

                    # user -> device
                    elif notified_socket == self.new_user_socket:
                        self.new_device_socket.send(message)

            for notified_socket in exception_sockets:
                self.sockets.remove(notified_socket)
                print(f"Proxy connection with {self.device.name} ended");
                # send empty message to disconnect new sockets
                if notified_socket == self.new_device_socket and self.new_user_socket:
                    self.new_user_socket.send('');
                else:
                    self.new_device_socket.send('')
                sys.exit()