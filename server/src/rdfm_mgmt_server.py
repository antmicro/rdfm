import socket
import select
import json
import sys
import jsonschema
import time
from flask import Flask
from threading import Thread
from typing import Optional
from rdfm_mgmt_communication import *
from proxy import Proxy

REQUEST_SCHEMA = {}
app = Flask(__name__)


@app.route('/')
def index():
    return create_alert({'devices': sorted(server.connected_devices.keys())})


@app.route('/device/<devicename>', methods=['GET'])
def device_metadata(devicename: str):
    return create_alert(server.connected_devices[devicename].metadata)


@app.route('/device/<devicename>/update')
def device_update(devicename: str):
    server.connected_devices[devicename].send({'method': 'update'})
    return {}


@app.route('/device/<devicename>/proxy')
def device_proxy(devicename: str):
    proxy = Proxy('127.0.0.1', None, server.connected_devices[devicename],
                  args.encrypted, args.cert, args.key)
    server.proxy_connections.append(proxy)
    t = Thread(target=proxy.run)
    t.start()

    while proxy._port is None:
        time.sleep(0.25)

    timeout = 5 * 60
    interval = 1
    start = time.time()
    while (proxy.proxy_device_socket is None and
           time.time() - start < timeout):
        time.sleep(interval)

    if proxy.proxy_device_socket:
        return create_alert({
            'message': 'shell ready to connect',
            'port': proxy._port
        })
    return 'Device proxy request timeout'


class Server:
    def __init__(self, hostname: str, port: int,
                 encrypted: bool, cert: str, cert_key: str):
        self._hostname: str = hostname
        self._port: int = port

        self.encrypted = encrypted
        self.cert: str = cert
        self.cert_key: str = cert_key

        self.proxy_connections: list[Proxy] = []

        self.server_socket: socket.socket = create_listening_socket(
                                                                hostname,
                                                                port,
                                                                self.encrypted,
                                                                self.cert,
                                                                self.cert_key)
        self.sockets: list[socket.socket] = [self.server_socket]

        self.connected_users: list[User] = []
        self.connected_devices: dict[str, Device] = {}
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
                self.connected_devices[client.name] = client

    def get_client_proxy_connections(self, client: Client) -> list[Proxy]:
        """Get a list of proxy connections that the client is involved in

        Args:
            client: Self explanatory

        Returns:
            List of currently opened proxy connections that include the client
        """
        return [p for p in self.proxy_connections
                if client == p.user or client == p.device]

    def disconnect_client(self, client_socket: socket.socket) -> None:
        """Stop monitoring the disconnected client.
        Remove it from the device or user containers and active sockets

        Args:
            client_socket: Detected disconnected client socket
        """
        # stop listening to this socket
        self.sockets.remove(client_socket)

        if client_socket not in self.clients:
            return
        # disconnect its proxies
        client = self.clients[client_socket]
        print("Disconnecting", client.name, "...")
        client_proxies = self.get_client_proxy_connections(client)
        print(len(client_proxies))
        for p in client_proxies:
            p.disconnect()
            self.proxy_connections.remove(p)

        # remove its client
        if isinstance(client, User):
            self.connected_users.remove(client)
        if isinstance(client, Device):
            del self.connected_devices[client.name]
            print('Disconnected device')
        del self.clients[client_socket]

    def handle_request(self, request: dict, client: Client) -> None:
        """Parse request and perform actions depending on the type

        Args:
            request: Request that the client received
            client: Recipent of the request
        """
        print(f'Request {request["method"]} from {client.name}')

        # Server requests
        if request['method'] == 'list':
            client.send(create_alert({
                'devices': sorted(self.connected_devices.keys())
            }))
            return

        # Device requests
        device = self.connected_devices[request['device_name']]
        assert device is not None

        if request['method'] == 'proxy':
            assert isinstance(client, User)
            proxy = Proxy(self._hostname, client, device,
                          self.encrypted, self.cert, self.cert_key)
            self.proxy_connections.append(proxy)
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
                    try:
                        (client_socket,
                         client_address) = self.server_socket.accept()
                    except Exception as e:
                        print('Error: ', e, file=sys.stderr)
                        continue
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
    parser.add_argument('-http_port', metavar='hp', type=int, default=5000,
                        help='listening port')
    parser.add_argument('-schemas', metavar='s', type=str,
                        default='json_schemas',
                        help='directory with requests schemas')
    parser.add_argument('-no_ssl', action='store_false', dest='encrypted',
                        help='turn off encryption')
    parser.add_argument('-cert', type=str, default='./certs/SERVER.crt',
                        help="""server cert file""")
    parser.add_argument('-key', type=str, default='./certs/SERVER.key',
                        help="""server cert key file""")
    args = parser.parse_args()

    with open(f'{args.schemas}/request_schema.json', 'r') as f:
        REQUEST_SCHEMA = json.loads(f.read())

    server = Server(args.hostname, args.port,
                    args.encrypted, args.cert, args.key)
    t = Thread(target=server.run, daemon=True)
    t.start()

    if args.encrypted:
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False,
                ssl_context=(args.cert, args.key))
    else:
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False)
