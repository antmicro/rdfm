from __future__ import annotations
import socket
import select
import re
from threading import Thread

from typing import Optional

from communication import *
from proxy import Proxy

class Server:
    def __init__(self, hostname: str, port: int):
        self._hostname = hostname
        self._port = port

        self.server_socket: socket.socket = create_listening_socket(hostname, port)
        self.sockets: list[socket.socket] = [self.server_socket]
        
        self.connected_users: list[User] = []
        self.connected_devices: list[Device] = []
        self.clients: list[dict[socket.socket, Client]] = {}
    
    def connect_client(self, client_registration_request: dict,
                        client_socket: socket.socket) -> None:
        """Start monitoring the connected client.
        Add it to the device or user containers and active sockets for data transmission

        Args:
            client_registration_request: Received client registration data
            client_socket: Newly connected client socket
        """
        print(f'client type: {client_registration_request["type"]}')
        client = create_client(client_registration_request['type'],
                                 client_registration_request['name'], client_socket)
        if client:
            self.clients[client_socket] = client
            self.sockets.append(client_socket)
            if isinstance(client, User):
                self.connected_users.append(client)
            if isinstance(client, Device):
                self.connected_devices.append(client)

    def disconnect_client(self, client_socket: socket.socket) -> None:
        """Stop monitoring the disconnected client.
        Remove it from the device or user containers and active sockets

        Args:
            client_socket: Detected disconnected client socket
        """
        client = self.clients[client_socket]
        if client:
            del self.clients[client_socket]
            self.sockets.remove(client_socket)
            if isinstance(client, User):
                self.connected_users.remove(client)
            if isinstance(client, Device):
                self.connected_devices.remove(client)
                print('disconnected device')

    def get_device_by_name(self, name: str) -> Optional[Device]:
        """Finds and returns connected device with specified name

        Args:
            name: The name of the device we're looking for

        Returns:
            Device with specified name if it's connected
        """
        for device in self.connected_devices:
            if device.name == name:
                return device
        return None
    
    def send_request_to_device(self, name: str, request: str) -> None:
        """Find device with given name and send request to it

        Args:
            name: Name of the device to send request to
            request: Name of the request

        Throws:
            NameError: There is no connected device with specified name
        """
        device: Device = self.get_device_by_name(name)
        try:
            device.send({ 'request': request })
            print('Sent request')
        except NameError:
            print(f'Error: There is no connected device named {name}')
    
    def broadcast_device_to_users(self, device: Device, message: dict) -> None:
        """Broadcast various information about the device to all connected users
        Example: Broadcasting that the new device has just connected

        Args:
            device: About which device we're broadcasting a message
            message: What information we want to broadcast
        """
        for user in self.connected_users:
            print(f'broadcasted to {user.name}')
            user.send({
                'device': device.name,
                'message': message
            })

    def handle_request(self, request: dict, client: Client) -> None:
        """Parse request and perform actions depending on the type

        Args:
            request: Request that the client received
            client: Recipent of the request
        """
        if request.startswith('REQ'):
            # parse request
            result = re.match(r"^REQ (.*?) (.*?)$", request)
            if result:
                device_name, request_type = result.group(1), result.group(2).lower()
                device = self.get_device_by_name(device_name)

                print(f'Request {request_type} from {client.name}')
                if device:
                    if request_type == 'proxy':
                        print(f'Received proxy request for {device_name}')
                        proxy = Proxy(self._hostname, client, device,)
                                        
                        t = Thread(target=proxy.run)
                        t.start()

                    elif request_type == 'info':
                        print(f'Received info request for {device_name}')
                        client.send(device.metadata)

                    elif request_type == 'refresh':
                        print(f'Received refresh request for {device_name}')
                        device.send('refresh')
                        pass

        elif request == 'LIST':
            devicenames: list[str] = [device.name for device in self.connected_devices]
            client.send({'Devices': sorted(devicenames)})
    
    def run(self):
        """Main server loop for receiving and sending requests"""
        print(f'Listening for connections on {self._hostname}:{self._port}...')

        while True:
            read_sockets, _, exception_sockets = select.select(self.sockets, [], self.sockets)

            # iterate over notified sockets
            for notified_socket in read_sockets:
                # new connection
                if notified_socket == self.server_socket:
                    client_socket, client_address = self.server_socket.accept()
                    client_registration_request: dict = receive_message(client_socket)
                    # disconnected immediately
                    if not client_registration_request:
                        continue
                    print('New connection', client_registration_request)

                    self.connect_client(client_registration_request, client_socket)
                    print('Accepted new connection from {}:{}, {}'
                        .format(*client_address, client_registration_request['name'],
                                self.clients[client_socket]))

                # existing socket sends message
                else:
                    message: dict = receive_message(notified_socket)

                    # identify sender
                    client: Client = self.clients[notified_socket]

                    # client disconnected
                    if not message:
                        print('Closed connection from: {}'.format(self.clients[notified_socket].name))
                        self.disconnect_client(client_socket)
                        continue

                    print(f'Received message from {client.name}: {message}')
                    print(message, type(message))

                    # broadcast message from device to listening users
                    if isinstance(client, Device):
                        if 'metadata' in message:
                            client.metadata = message['metadata']
                        self.broadcast_device_to_users(client, message)

                    else:
                        self.handle_request(message, client)

            # exceptions
            for notified_socket in exception_sockets:
                self.sockets_list.remove(notified_socket)
                del self.clients[notified_socket]

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='rdfm-mgmt-shell server instance.')
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the host')
    parser.add_argument('-port', metavar='p', type=int, default=1234,
                        help='listening port')
    args = parser.parse_args()

    server = Server(args.hostname, args.port)
    server.run()