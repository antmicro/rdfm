import socket
import select
import sys
import json
import time
from flask import Flask
from threading import Thread
from typing import Optional
from rdfm_mgmt_communication import *
from request_models import *
from proxy import Proxy

app = Flask(__name__)


@app.route('/')
def index():
    return Alert(alert={
        'devices': sorted(server.connected_devices.keys())
    }).json()


@app.route('/device/<devicename>', methods=['GET'])
def device_metadata(devicename: str):
    return Alert(  # type: ignore
        alert=server.connected_devices[devicename].metadata
    ).json()


@app.route('/device/<devicename>/update')
def device_update(devicename: str):
    server.connected_devices[devicename].send(UpdateRequest())  # type: ignore
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
        return Alert(alert={  # type: ignore
            'message': 'shell ready to connect',
            'port': proxy._port
        }).json()
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

        self.file_transfers: list[FileTransfer] = []

    def connect_client(self, new_client_data: ClientRequest,
                       client_socket: socket.socket) -> None:
        """Start monitoring the connected client.
        Add it to the device or user containers and active sockets for
        data transmission

        Args:
            new_client_data: Client metadata from the new client request
            client_socket: Newly connected client socket
        """
        print(f'client group: {new_client_data.group}')
        client = create_client(new_client_data.group,
                               new_client_data.name, client_socket)
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
        print(f'Closing {len(client_proxies)} proxy connections')
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

    def handle_request(self, request: Request, client: Client) -> None:
        """Parse request and perform actions depending on the type

        Args:
            request: Request that the client received
            client: Recipent of the request
        """

        match request:
            case InfoDeviceRequest(device_name=device_name):
                client.send(Alert(  # type: ignore
                    alert=self.connected_devices[device_name].metadata
                ))
            case UpdateDeviceRequest(device_name=device_name):
                self.connected_devices[device_name].send(
                    UpdateRequest()  # type: ignore
                )
            case ProxyDeviceRequest(device_name=device_name):
                assert isinstance(client, User)
                proxy = Proxy(self._hostname, client,
                              self.connected_devices[device_name],
                              self.encrypted, self.cert, self.cert_key)
                t = Thread(target=proxy.run)
                t.start()
            # TODO: move file transfer to another thread
            case DownloadDeviceRequest(device_name=device_name,
                                       file_path=file_path):
                print('Registered new file transfer')
                device = self.connected_devices[device_name]
                self.file_transfers.append(
                    FileTransfer(client, device, file_path)
                )
                device.send(
                    DownloadRequest(file_path=file_path)  # type: ignore
                )
            case UploadDeviceRequest(device_name=device_name,
                                     file_path=file_path):
                print('Registered new file transfer')
                device = self.connected_devices[device_name]
                self.file_transfers.append(
                    FileTransfer(device, client, file_path)
                )
                device.send(UploadRequest(file_path=file_path))  # type: ignore
            case ListRequest():
                client.send(Alert(alert={  # type: ignore
                    'devices': sorted(self.connected_devices.keys())
                }))
            case SendFileRequest(file_path=file_path):
                matching_transfers = filter(
                    lambda transfer:
                        (transfer.sender == client and
                         transfer.file_path == file_path),
                    self.file_transfers
                )
                receivers: list[Client] = [t.receiver
                                           for t in matching_transfers]
                for receiver in receivers:
                    receiver.send(request)
            case FileCompletedRequest(file_path=file_path):
                matching_transfers = filter(
                    lambda transfer:
                        (transfer.receiver == client and
                         transfer.file_path == file_path),
                    self.file_transfers
                )
                for transfer in matching_transfers:
                    self.file_transfers.remove(transfer)
            case Metadata(metadata=metadata):
                assert isinstance(client, Device)
                client.metadata = metadata

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
                    register_request: Optional[Request] = receive(
                                                            client_socket)

                    # disconnected immediately
                    if not register_request:
                        continue
                    assert isinstance(register_request, RegisterRequest)
                    print('New connection', register_request)

                    self.connect_client(register_request.client, client_socket)
                    print('Accepted new connection from {}:{}, {}'
                          .format(*client_address,
                                  register_request.client.name,
                                  self.clients[client_socket]))

                # existing socket sends message
                else:
                    message: Optional[Request] = None
                    # identify sender
                    client: Client = self.clients[notified_socket]

                    try:
                        message = receive(notified_socket)
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
    parser.add_argument('-no_ssl', action='store_false', dest='encrypted',
                        help='turn off encryption')
    parser.add_argument('-cert', type=str, default='./certs/SERVER.crt',
                        help="""server cert file""")
    parser.add_argument('-key', type=str, default='./certs/SERVER.key',
                        help="""server cert key file""")
    args = parser.parse_args()

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
