import socket
import select
import sys
import time
from threading import Thread
from typing import Optional
from rdfm_mgmt_communication import *
from request_models import *
from proxy import Proxy


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

        client = create_client(new_client_data.group,
                               new_client_data.name, client_socket,
                               new_client_data.capabilities)
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

    def handle_request(self, request: Request,
                       client: Optional[Client] = None) -> Optional[Request]:
        """Parse request and perform actions depending on the type

        Args:
            request: Request that the client received
            client: Request sender if sent via client not HTTP

        Returns:
            Optional response to request sender
        """

        if isinstance(request, DeviceRequest):
            if request.device_name not in self.connected_devices:
                return Alert(alert={  # type: ignore
                    'error': 'Device not found'
                })
            else:
                device = self.connected_devices[request.device_name]
                if not device.can_handle_request(request.method):
                    return Alert(alert={  # type: ignore
                        'error': (f"Requested device doesn't provide necessary"
                                  "capabilities:"),
                        "requested_capabilities":
                            device.required_capabilities[request.method]})

        match request:
            case InfoDeviceRequest(device_name=_):
                return Alert(  # type: ignore
                    alert={
                        "metadata": device.metadata,
                        "capabilities": device.capabilities
                    }
                )
            case UpdateDeviceRequest(device_name=_):
                device.send(
                    UpdateRequest()  # type: ignore
                )
                return Alert(  # type: ignore
                    alert={'message': 'Send update request to the device'}
                )
            case ProxyDeviceRequest(device_name=_):
                client = client if isinstance(client, User) else None
                proxy = Proxy(self._hostname, client, device,
                              self.encrypted, self.cert, self.cert_key)
                t = Thread(target=proxy.run)
                t.start()

                while proxy.port is None:
                    time.sleep(0.25)

                timeout = 30
                interval = 1
                start = time.time()
                while (proxy.proxy_device_socket is None and
                        time.time() - start < timeout):
                    time.sleep(interval)

                if proxy.proxy_device_socket:
                    return Alert(alert={  # type: ignore
                        'message': 'shell ready to connect',
                        'port': proxy.port
                    })
                return Alert(alert={  # type: ignore
                    'message': 'Device proxy request timeout'
                })

            # TODO: move file transfer to another thread
            case DownloadDeviceRequest(device_name=_, file_path=file_path):
                print('Registered new file transfer')
                assert client is not None
                self.file_transfers.append(
                    FileTransfer(client, device, file_path)
                )
                device.send(
                    DownloadRequest(file_path=file_path)  # type: ignore
                )
                return Alert(alert={  # type: ignore
                    'message': 'Downloading file...'
                })
            case UploadDeviceRequest(device_name=_, file_path=file_path,
                                     src_file_path=_):
                print('Registered new file transfer')
                self.file_transfers.append(
                    FileTransfer(device, client, file_path)
                )
                device.send(UploadRequest(file_path=file_path))  # type: ignore
                return Alert(alert={  # type: ignore
                    'message': 'Uploading file...'
                })
            case ListRequest():
                return Alert(alert={  # type: ignore
                    'devices': sorted(self.connected_devices.keys())
                })
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
                return None
            case FileCompletedRequest(file_path=file_path):
                matching_transfers = filter(
                    lambda transfer:
                        (transfer.receiver == client and
                         transfer.file_path == file_path),
                    self.file_transfers
                )
                for transfer in matching_transfers:
                    self.file_transfers.remove(transfer)
                return None
            case Metadata(metadata=metadata):
                assert isinstance(client, Device)
                client.metadata = metadata
                return None
        return None

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
                    response: Optional[Request] = self.handle_request(message,
                                                                      client)
                    if response:
                        client.send(response)

            # exceptions
            for notified_socket in exception_sockets:
                self.disconnect_client(notified_socket)
