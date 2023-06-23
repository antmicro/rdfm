import socket
import select
import json
import jsonschema
from threading import Thread
from typing import Optional
from rdfm_mgmt_communication import *
from proxy import Proxy

REQUEST_SCHEMA = {}


class Server:
    def __init__(self, hostname: str, port: int):
        self._hostname: str = hostname
        self._port: int = port

        self.server_socket: socket.socket = create_listening_socket(
            hostname, port)
        self.sockets: list[socket.socket] = [self.server_socket]

        self.connected_users: list[User] = []
        self.connected_devices: list[Device] = []
        self.clients: dict[socket.socket, Client] = {}

    def connect_client(self, new_client_data: dict,
                       client_socket: socket.socket) -> None:
        """Start monitoring the connected client.
        Add it to the device or user containers and active sockets for
        data transmission

        Args:
            new_client_data: Client metadata from the new client request
            client_socket: Newly connected client socket
        """
        print(f'client group: {new_client_data["group"]}')
        client = create_client(new_client_data['group'],
                               new_client_data['name'], client_socket)
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
        if client_socket in self.clients:
            client = self.clients[client_socket]
            del self.clients[client_socket]
            self.sockets.remove(client_socket)
            if isinstance(client, User):
                self.connected_users.remove(client)
            if isinstance(client, Device):
                self.connected_devices.remove(client)
                print('Disconnected device')

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

    def handle_request(self, request: dict, client: Client) -> None:
        """Parse request and perform actions depending on the type

        Args:
            request: Request that the client received
            client: Recipent of the request
        """
        print(f'Request {request["method"]} from {client.name}')

        # Server requests
        if request['method'] == 'list':
            devicenames: list[str] = [
                device.name for device in self.connected_devices]
            client.send(create_alert({'devices': sorted(devicenames)}))
            return

        # Device requests
        device = self.get_device_by_name(request['device_name'])
        assert device is not None

        if request['method'] == 'proxy':
            assert isinstance(client, User)
            proxy = Proxy(self._hostname, client, device)
            t = Thread(target=proxy.run)
            t.start()

        elif request['method'] == 'info':
            client.send(create_alert(device.metadata))

        elif request['method'] == 'update':
            device.send({'method': 'update'})

    def run(self) -> None:
        """Main server loop for receiving and sending requests"""
        print(f'Listening for connections on {self._hostname}:{self._port}...')

        while True:
            read_sockets, _, exception_sockets = select.select(
                self.sockets, [], self.sockets)

            # iterate over notified sockets
            for notified_socket in read_sockets:
                # new connection
                if notified_socket == self.server_socket:
                    client_socket, client_address = self.server_socket.accept()
                    registration_request: Optional[dict] = receive_message(
                                                                client_socket)

                    # disconnected immediately
                    if not registration_request:
                        continue
                    assert registration_request is not None
                    jsonschema.validate(instance=registration_request,
                                        schema=REQUEST_SCHEMA)
                    print('New connection', registration_request)

                    self.connect_client(
                        registration_request['client'], client_socket)
                    print('Accepted new connection from {}:{}, {}'
                          .format(*client_address,
                                  registration_request['client']['name'],
                                  self.clients[client_socket]))

                # existing socket sends message
                else:
                    message: Optional[dict] = None
                    # identify sender
                    client: Client = self.clients[notified_socket]

                    try:
                        message = receive_message(notified_socket)
                        if not message:
                            # client disconnected
                            print('Closed connection from:',
                                  self.clients[notified_socket].name)
                            self.disconnect_client(notified_socket)
                            break
                    except Exception:
                        # received invalid request
                        continue
                    assert message is not None

                    # identify sender
                    print(f'Received message from {client.name}: {message}')

                    if isinstance(client, Device):
                        if 'metadata' in message:
                            client.metadata = message['metadata']

                    else:
                        self.handle_request(message, client)

            # exceptions
            for notified_socket in exception_sockets:
                self.disconnect_client(notified_socket)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='rdfm-mgmt-shell server instance.')
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the host')
    parser.add_argument('-port', metavar='p', type=int, default=1234,
                        help='listening port')
    parser.add_argument('-schemas', metavar='s', type=str,
                        default='json_schemas',
                        help='directory with requests schemas')
    args = parser.parse_args()

    with open(f'{args.schemas}/request_schema.json', 'r') as f:
        REQUEST_SCHEMA = json.loads(f.read())

    server = Server(args.hostname, args.port)
    server.run()
