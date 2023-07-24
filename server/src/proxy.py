import socket
import select
import sys
import os
from typing import Optional, Final
from rdfm_mgmt_communication import *
from request_models import ProxyRequest, Alert

PROXY_BUFFER_SIZE: Final = 4096


class Proxy:
    def __init__(self, hostname: str, user: Optional[User], device: Device,
                 encrypted: bool = False, crt: str = "", key: str = ""):
        """Creates a proxy connection between user and device

        Here a new server listening socket is created.
        The device receives a message containing the new port and connects with
        reverse shell to it.
        After the device connects user receives message about the new port to
        connect to.
        If a client disconnects the proxy should send disconnect message to
        the client it was connected by proxy with.
        Also proxy socket should close, without disrupting other existing
        connections and server stability.

        Args:
            hostname: IP addr of the server
            user: User that required proxy connection, None if HTTP requested
            device: Device that the user requested to connect to
            encrypted: Whether connection should use SSL
            crt: File with server certificate
            key: File with certificate key
        """
        self.device: Device = device
        self.user: Optional[User] = user

        self.proxy_device_socket: Optional[socket.socket] = None
        self.proxy_user_socket: Optional[socket.socket] = None

        # creating new server listening socket
        self.proxy_socket: socket.socket = create_listening_socket(hostname, 0,
                                                                   encrypted,
                                                                   crt, key)
        self.sockets: list[socket.socket] = [self.proxy_socket]

        self._hostname: str = self.proxy_socket.getsockname()[0]
        self.port: int = self.proxy_socket.getsockname()[1]
        print(f'Opened proxy socket at {self.port} for dev',
              f'{self.device.name}, pid {os.getpid()}', )

    def send_connection_request(self) -> None:
        """Send connection request and new port to the device"""
        self.device.send(ProxyRequest(port=self.port))  # type: ignore

    def disconnect(self) -> None:
        """Sends empty message to proxy sockets to disconnect them"""
        try:
            for s in [self.proxy_socket,
                      self.proxy_device_socket,
                      self.proxy_user_socket]:
                if s:
                    assert s is not None
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()
            print("Disconnected proxy")
        except Exception as e:
            print("Error during proxy disconnect:", str(e))

    def run(self) -> None:
        """Main proxy loop for forwarding messages between user and device.
        Started with sending a connection request to the device so it connects
        with a new socket"""

        self.send_connection_request()
        while True:
            read_sockets, _, exception_sockets = select.select(self.sockets,
                                                               [],
                                                               self.sockets)
            for notified_socket in read_sockets:
                # someone new connected to the proxy
                if notified_socket == self.proxy_socket:
                    # assume that device should connect first
                    if not self.proxy_device_socket:
                        (self.proxy_device_socket,
                         new_device_address) = self.proxy_socket.accept()
                        assert self.proxy_device_socket is not None
                        print("Device connected to proxy:", new_device_address)

                        device_message: bytes = self.proxy_device_socket.recv(
                                                            PROXY_BUFFER_SIZE)
                        # disconnected immediately
                        if not device_message:
                            self.disconnect()
                            continue

                        self.sockets.append(self.proxy_device_socket)
                    # user connected
                    else:
                        (self.proxy_user_socket,
                         new_user_address) = self.proxy_socket.accept()
                        assert self.proxy_user_socket is not None
                        print(f"User connected to proxy: {new_user_address}")
                        self.proxy_user_socket.send(device_message)
                        self.sockets.append(self.proxy_user_socket)

                elif notified_socket in [self.proxy_device_socket,
                                         self.proxy_user_socket]:
                    message: bytes = notified_socket.recv(PROXY_BUFFER_SIZE)
                    # client disconnected from proxy connection
                    # close it and exit thread
                    if not message:
                        print(f'Closed proxy socket at {self.port}')
                        self.disconnect()
                        sys.exit()

                    # device -> user
                    if (notified_socket == self.proxy_device_socket and
                            self.proxy_user_socket):
                        assert self.proxy_user_socket is not None
                        self.proxy_user_socket.send(message)

                    # user -> device
                    elif notified_socket == self.proxy_user_socket:
                        assert self.proxy_device_socket is not None
                        self.proxy_device_socket.send(message)

            for notified_socket in exception_sockets:
                self.sockets.remove(notified_socket)
                print(f"Proxy connection with {self.device.name} ended")
                # send empty message to disconnect proxy sockets
                self.disconnect()
                sys.exit()
