import socket
import errno
import sys
import os
import pty
from threading import Thread

from communication import *

def connect_reverse(host: str, port: int) -> None:
    """Creates reverse shell connection with the server

    Args:
        host: Hostname of the server
        port: At which port to connect to the server
    """
    print(f'Connecting to proxy at {port}')
    s: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    # open shell
    os.dup2(s.fileno(),0)
    os.dup2(s.fileno(),1)
    os.dup2(s.fileno(),2)
    pty.spawn("/bin/sh")

def recv_loop(client: Client) -> None:
    """Receive packets from the server

    Args:
        client: Receiving client

    Throws:
        IOError: There is no upcoming data
    """
    while True:
        try:
            # loop over all received messages
            while True:
                message: Optional[dict] = client.receive()
                if message is None:
                    # server closed
                    print('Connection closed by the server')
                    sys.exit()
                assert message is not None

                client_response = client.handle_request(message)
                if client_response:
                    client.send(client_response)
                print('\r', message, end=f'\n{client.name} > ')

                # Print message
                if 'request' in message:
                    if message['request'] == 'proxy':
                        print('received proxy request')
                        t = Thread(target=connect_reverse,
                                   args=(client.get_server_addr()[0], message['port']))
                        t.start()

        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Reading error: {}'.format(str(e)))
                sys.exit()

        except Exception as e:
            print('Reading error: ', e)
            sys.exit()

def send_loop(client: Client) -> None:
    """Send messages to the server

    Args:
        server: Listening server socket
    """
    while True:
        message = input(f'{client.name} > ')

        if message:
            client.send(message)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='rdfm-mgmt-shell server instance.')
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the server')
    parser.add_argument('-port', metavar='p', type=int, default=1234,
                        help='listening port on the server')
    parser.add_argument('client_type', type=str.upper, choices=['USER', 'DEVICE'],
                        help='client type')
    parser.add_argument('name', type=str,
                        help='client name for identification, without whitespaces')
    parser.add_argument('-file', metavar='f', type=str, default='',
                        help='file containing device metadata')
    args = parser.parse_args()

    client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((args.hostname, args.port))

    # send registration
    client: Optional[Client] = create_client(args.client_type, args.name, client_socket)
    assert client is not None
    if isinstance(client, Device):
        client.metadata_file = args.file
    client.send(client.registration_packet(args.client_type, args.name))

    t = Thread(target=recv_loop, args=(client,))
    t.start()
    send_loop(client)