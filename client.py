import socket
import errno
import sys
import os
import pty
import json
from threading import Thread

from communication import *

def connect_reverse(host: str, port: int) -> None:
    """Creates reverse shell connection with the server

    Args:
        port: At which port to connect to the server
    """
    print(f'Connecting to proxy at {port}')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    # open shell
    os.dup2(s.fileno(),0)
    os.dup2(s.fileno(),1)
    os.dup2(s.fileno(),2)
    pty.spawn("/bin/sh")

def recv_from_server(server: socket.socket) -> None:
    """Receive packets from the server

    Args:
        server: Socket of the server we're connected to
    """
    while True:
        try:
            # loop over all received messages
            while True:
                message_header: bytes = server.recv(HEADER_LENGTH)
                
                if not message_header:
                    # server closed
                    print('Connection closed by the server')
                    sys.exit()
                    
                message_length: int = int(decode_json(message_header))
                message: dict = json.loads(server.recv(message_length).decode('utf-8'))
                print(message)

                # Print message
                if 'request' in message:
                    if message['request'] == 'proxy':
                        print('received proxy request')
                        t = Thread(target=connect_reverse,
                                   args=(server.getsockname()[0], message['port']))
                        t.start()

        except IOError as e:
            # when there are no incoming data error is going to be raised
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Reading error: {}'.format(str(e)))
                sys.exit()

            # we did not receive anything
            continue

        except Exception as e:
            print('Reading error: '.format(str(e)))
            sys.exit()

def send_to_server(server: socket.socket) -> None:
    """Send messages to the server

    Args:
        server: Listening server socket
    """
    while True:
        message = input(f'{client.name} > ')

        if message:
            server.send(encode_json(message))

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
    args = parser.parse_args()

    client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((args.hostname, args.port))

    # send registration
    client: Client = register_client(args.client_type, args.name, client_socket)
    client_socket.send(client.registration_packet(args.client_type, args.name))

    t = Thread(target=recv_from_server, args=(client_socket,))
    t.start()
    send_to_server(client_socket)