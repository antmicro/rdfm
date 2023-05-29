from __future__ import annotations
import socket
import select
import sys
import re
from threading import Thread

from typing import Optional

from communication import *

connected_users: list[User] = []
connected_devices: list[Device] = []
clients: list[dict[socket.socket, Client]] = {}

def broadcast_device_to_users(device: Device, message: dict) -> None:
    """Broadcast various information about the device to all connected users
    Example: Broadcasting that the new device has just connected

    Args:
        device: About which device we're broadcasting a message
        message: What information we want to broadcast
    """
    for user in connected_users:
        print(f'broadcasted to {user.name}')
        user.socket.send(encode_json({
            'device': device.name,
            'message': message
        }))

def send_request_to_device(name: str, request: str) -> None:
    """Find device with given name and send request to it

    Args:
        name: Name of the device to send request to
        request: Name of the request

    Throws:
        NameError: There is no connected device with specified name
    """
    device: Device = get_device_by_name(name)
    try:
        device.socket.send(encode_json({ 'request': request }))
        print('Sent request')
    except NameError:
        print(f'Error: There is no connected device named {name}')
    

def get_device_by_name(name: str) -> Optional[Device]:
    """Finds and returns connected device with specified name

    Args:
        name: The name of the device we're looking for

    Returns:
        Device with specified name if it's connected
    """
    for device in connected_devices:
        if device.name == name:
            return device
    return None

def connect_client(client: dict, client_socket: socket.socket, sockets: list[socket.socket]) -> None:
    """Start monitoring the connected client.
    Add it to the device or user containers and active sockets for data transmission

    Args:
        client: Received client registration data
        client_socket: Newly connected client socket
        sockets: Container with active monitored sockets
    """
    print(f'client type: {type(client)}')
    client = register_client(new_client['type'], new_client['name'], client_socket)
    if client:
        clients[client_socket] = client
        sockets.append(client_socket)
        if isinstance(client, User):
            connected_users.append(client)
        if isinstance(client, Device):
            connected_devices.append(client)

def disconnect_client(client_socket: socket.socket, sockets: list[socket.socket]):
    """Stop monitoring the disconnected client.
    Remove it from the device or user containers and active sockets

    Args:
        client_socket: Detected disconnected client socket
        sockets: Container with active monitored sockets
    """
    client = clients[client_socket]
    if client:
        del clients[client_socket]
        sockets.remove(client_socket)
        if isinstance(client, User):
            connected_users.remove(client)
        if isinstance(client, Device):
            connected_devices.remove(client)
            print('disconnected device')


def proxy(host: str, user: User, device: Device) -> None:
    """Creates a proxy connection between user and device

    Here a new server listening socket is created.
    The device receives a message containing the new port and connects with reverse shell to it.
    After the device connects user receives message about the new port to connect to.
    If 

    Args:
        host: Hostname of the server
        user: User that required proxy connection
        device: Device that the user specified to connect to
    """

    # creating new server listening socket
    proxy_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind((host, 0))
    proxy_socket.listen()
    proxy_sockets_list: list[socket.socket] = [proxy_socket]
    proxy_port: int = proxy_socket.getsockname()[1]
    print(f'Opened proxy socket at {proxy_port} (user: {user.name}, device: {device.name})')

    # send connection request and new port to the device
    device.socket.send(encode_json({
        'request': 'proxy',
        'port': proxy_port
    }))

    new_device_socket = None
    new_user_socket = None

    while True:
        read_sockets, _, exception_sockets = select.select(proxy_sockets_list, [], proxy_sockets_list)
        for notified_socket in read_sockets:
            # someone new connected to the proxy
            if notified_socket == proxy_socket:
                # assume that device should connect first
                if not new_device_socket:
                    new_device_socket, new_device_address = proxy_socket.accept()
                    print(f"Device connected to proxy: {new_device_address}")
                
                    device_message: bytes = new_device_socket.recv(4096)
                    # disconnected immediately
                    if not device_message:
                        continue

                    proxy_sockets_list.append(new_device_socket)
                    # send connection invitation to the user
                    user.socket.send(
                        encode_json({'message': f'connect to shell at {proxy_port}'})
                    )
                # user connected
                else:
                    new_user_socket, new_user_address = proxy_socket.accept()
                    print(f"User connected to proxy: {new_user_address}")
                    new_user_socket.send(device_message)
                    proxy_sockets_list.append(new_user_socket)

            elif notified_socket in [new_device_socket, new_user_socket]:
                message = notified_socket.recv(4096)
                # client disconnected from proxy connection - close it and exit thread
                if not message:
                    print(f'Closed proxy socket at {proxy_port} (user: {user.name}, device: {device.name})')
                    sys.exit()
                
                # device -> user
                if notified_socket == new_device_socket:
                    new_user_socket.send(message)

                # user -> device
                elif notified_socket == new_user_socket:
                    new_device_socket.send(message)

        for notified_socket in exception_sockets:
            proxy_sockets_list.remove(notified_socket)
            print(f"Proxy connection with {device.name} ended");
            # send empty message to disconnect new sockets
            if notified_socket == new_device_socket and new_user_socket:
                new_user_socket.send('');
            else:
                new_device_socket.send('')
            sys.exit()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='rdfm-mgmt-shell server instance.')
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the host')
    parser.add_argument('-port', metavar='p', type=int, default=1234,
                        help='listening port')
    args = parser.parse_args()
    
    server_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((args.hostname, args.port))
    server_socket.listen()
    
    print(f'Listening for connections on {args.hostname}:{args.port}...')

    # list of sockets for select.select()
    sockets_list: list[socket.socket] = [server_socket]
    while True:
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        # iterate over notified sockets
        for notified_socket in read_sockets:
            # new connection
            if notified_socket == server_socket:
                client_socket, client_address = server_socket.accept()
                new_client: dict = receive_message(client_socket)
                # disconnected immediately
                if not new_client:
                    continue
                print('New connection', new_client)

                connect_client(new_client, client_socket, sockets_list)
                print('Accepted new connection from {}:{}, {}'
                    .format(*client_address, new_client['name'], clients[client_socket]))

            # existing socket sends message
            else:
                message: dict = receive_message(notified_socket)

                # identify sender
                client: Client = clients[notified_socket]

                # client disconnected
                if not message:
                    print('Closed connection from: {}'.format(clients[notified_socket].name))
                    disconnect_client(client_socket, sockets_list)
                    continue

                print(f'Received message from {client.name}: {message}')
                print(message, type(message))

                # broadcast message from device to listening users
                if isinstance(client, Device):
                    broadcast_device_to_users(client, message)

                else:
                    if message.startswith('REQ'):
                        # parse request
                        result = re.match(r"^REQ (.*?) (.*?)", message)
                        if result:
                            device_name, request = result.group(1, 2)
                            print(f'Sending request {request} to {device_name}')
                            print(client.name)
                            t = Thread(target=proxy, args=(args.hostname, client, get_device_by_name(device_name)),)
                            t.start()

                    elif message == 'LIST':
                        devicenames: list[str] = [device.name for device in connected_devices]
                        notified_socket.send(encode_json({'Devices': sorted(devicenames)}))

        # exceptions
        for notified_socket in exception_sockets:
            sockets_list.remove(notified_socket)
            del clients[notified_socket]