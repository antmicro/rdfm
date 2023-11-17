import socket
import select
import sys
import jwt
from threading import Thread
from typing import Optional
from rdfm_mgmt_communication import *
from request_models import *
from file_transfer import FileTransfer
from proxy import Proxy
from database.devices import DevicesDB
from database.packages import PackagesDB
from database.groups import GroupsDB
from database.registrations import RegistrationsDB
import database.db
import configuration
from device_mgmt.containers import RemoteDevices, ShellSessions


CONNECTION_TRIES = 2


class Server:
    def __init__(self, config: configuration.ServerConfig):
        self._hostname: str = config.hostname
        self._port: int = config.port

        self.encrypted = config.encrypted
        self.cert: str = config.cert
        self.cert_key: str = config.key

        self.jwt_secret = config.jwt_secret

        self.proxy_connections: list[Proxy] = []

        self.server_socket: socket.socket = create_listening_socket(
            config.hostname,
            config.port,
            self.encrypted,
            self.cert,
            self.cert_key)
        self.sockets: list[socket.socket] = [self.server_socket]

        self.connected_users: list[User] = []
        self.clients: dict[socket.socket, Client] = {}
        self.connected_devices: dict[str, Device] = {}

        self.db = database.db.create(config.db_conn)
        self._devices_db: DevicesDB = DevicesDB(self.db)
        self._packages_db: PackagesDB = PackagesDB(self.db)
        self._groups_db: GroupsDB = GroupsDB(self.db)
        self._registrations_db: RegistrationsDB = RegistrationsDB(self.db)
        self.remote_devices = RemoteDevices()
        self.shell_sessions = ShellSessions()

        # filename in server cache -> transfer object
        self.file_transfers: dict[str, FileTransfer] = {}

    def create_mock_data(self):
        """ Creates mock data

        Fills the database with mock data to be used for testing purposes
        This does not check if the data was previously inserted, it is
        assumed that for tests a clean database is always used.
        """
        print("WARNING: Creating mock data in the database")
        print("WARNING: Do not use in production!")

        # Create dummy devices
        self._devices_db.insert_device(
            Device("foo", None, "00:00:00:00:00:00", {}))
        self._devices_db.insert_device(
            Device("bar", None, "11:11:11:11:11:11", {}))
        self._devices_db.insert_device(
            Device("baz", None, "22:22:22:22:22:22", {}))

    def can_device_register(self, register_request: RegisterRequest,
                            device_socket: socket.socket) -> bool:
        """Decides if device can register in our server

        Args:
            register_request: Register request sent by device client
            device_socket: Socket with which server tries to connect

        Returns:
            Can device client register in our server
        """
        # here can be placed some logic that decides if device can
        # connect to our server
        # example: ban list of ip or types of devices, or capabilities rules
        return True

    def register_device(self, register_request: RegisterRequest,
                        device_socket: socket.socket
                        ) -> Alert | AuthTokenRequest:

        if not self.can_device_register(register_request, device_socket):
            return Alert(alert={  # type: ignore
                'error': 'Device registration refused'
            })

        device_data: ClientRequest = register_request.client

        assert device_data.name is not None
        assert device_data.mac_address is not None
        assert device_data.capabilities is not None
        device = Device(device_data.name, device_socket,
                        device_data.mac_address,
                        device_data.capabilities)
        self._devices_db.insert_device(device)
        self.connected_devices[device_data.name] = device
        self.clients[device_socket] = device
        self.sockets.append(device_socket)

        token = jwt.encode(
            {
                "name": device_data.name,
                "mac_address": device_data.mac_address
            },
            self.jwt_secret, algorithm="HS256"
        )
        return AuthTokenRequest(jwt=token)  # type: ignore

    def authorize_device(self,
                         auth_request: AuthTokenRequest | RegisterRequest,
                         device_socket: socket.socket
                         ) -> Alert | AuthTokenRequest:
        """If device connects for the first time (sends registration request
        instead of JWT token) it checks if it is authorized and generates
        JWT token, else checks JWT token

        Args:
            auth_request: Device client auth request (register or JWT token)
            device_socket: New socket of device client sending request

        Returns:
            Message containing JWT token or authorization success message
        """

        try:
            # device client auth with token
            assert isinstance(auth_request, AuthTokenRequest)
            print('Device trying to auth with JWT')
            try:
                decoded = jwt.decode(auth_request.jwt, self.jwt_secret,
                                     algorithms=["HS256"])
                device = self._devices_db.get_device(
                    decoded['name'], decoded['mac_address']
                )
                if device:
                    device.set_socket(device_socket)
                    self.connected_devices[decoded['name']] = device
                    self.clients[device_socket] = device
                    self.sockets.append(device_socket)
                    return Alert(alert={  # type: ignore
                        'message': f'Connected as {device.name}'
                    })
                else:
                    print("No device in database")
                    return Alert(alert={  # type: ignore
                        'error': 'Device not found in database'
                    })
            except Exception as e:
                error_msg = f'JWT token validation failed", {str(e)}'
                print(error_msg)
                Alert(alert={  # type: ignore
                    'error': error_msg
                })
            return Alert(alert={  # type: ignore
                'error': 'Connection failed'
            })

        except Exception:
            # device client auth without token
            print('Device trying to connect without JWT')
            print(type(auth_request))
            assert isinstance(auth_request, RegisterRequest)
            return self.register_device(auth_request, device_socket)

    def connect_client(self,
                       connect_request: AuthTokenRequest | RegisterRequest,
                       client_socket: socket.socket
                       ) -> Alert | AuthTokenRequest:
        """Start monitoring the connected client.
        Add it to the device or user containers and active sockets for
        data transmission

        Args:
            connect_request: New client request
            client_socket: Newly connected client socket

        Returns:
            reply for client
        """

        print('Trying to connect client...')
        # currently only device clients use JWT
        if (isinstance(connect_request, AuthTokenRequest) or
                connect_request.client.group == ClientGroups.DEVICE):
            res = self.authorize_device(connect_request, client_socket)
            print(res)
            return res
        else:
            new_client_data = connect_request.client
            client: Optional[Client] = create_client(
                new_client_data.group,
                new_client_data.name,
                client_socket,
                new_client_data.capabilities)
            if client:
                assert isinstance(client, User)
                self.connected_users.append(client)
                self.clients[client_socket] = client
                self.sockets.append(client_socket)
                return Alert(alert={  # type: ignore
                    'message': f'Connected as {new_client_data.name}'
                })
            else:
                return Alert(alert={  # type: ignore
                    'error': 'Connection refused'
                })

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

                if wait_at_most(60, 0.25, lambda: proxy.port is not None):
                    if wait_at_most(30, 1,
                                    lambda: proxy.proxy_device_socket):
                        return Alert(alert={  # type: ignore
                            'message': 'shell ready to connect',
                            'port': proxy.port
                        })
                return Alert(alert={  # type: ignore
                    'message': 'Device proxy request timeout'
                })
            case ListRequest():
                return Alert(alert={  # type: ignore
                    'devices': sorted(self.connected_devices.keys())
                })
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

                    # 2 tries for device connection
                    # if JWT fails, try with register request
                    for try_nr in range(CONNECTION_TRIES):
                        connection_request: Optional[Request] = receive(
                            client_socket)
                        print("Received connection request",
                              connection_request)

                        # disconnected immediately
                        if not connection_request:
                            continue
                        assert (isinstance(connection_request,
                                           RegisterRequest) or
                                isinstance(connection_request,
                                           AuthTokenRequest))

                        connection_response: Request = self.connect_client(
                            connection_request,
                            client_socket)
                        client_socket.send(encode_json(connection_response))
                        if (not isinstance(connection_response, Alert) or
                                'error' not in connection_response.alert):
                            print('Accepted new connection from {}:{}, {}'
                                  .format(*client_address,
                                          self.clients[client_socket].name,
                                          self.clients[client_socket]))
                            break
                        elif try_nr == CONNECTION_TRIES - 1:
                            # refuse connection
                            client_socket.close()

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


""" Global instance of the RDFM server
"""
instance: Optional[Server] = None
