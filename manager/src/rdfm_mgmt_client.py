import socket
import errno
import sys
import os
import jsonschema
import json
import ssl
from typing import Optional
from threading import Thread
from rdfm_mgmt_communication import Client, create_client

REQUEST_SCHEMA: dict = {}
CLIENT_TYPE = "USER"


def parse_request(user_input: str) -> Optional[dict]:
    """Parses user input to the JSON request

    Args:
        user_input: Input received from the user shell
        example: "REQ d1 proxy"

    Returns:
        JSON request according to the schema
    """
    request = {
        'method': '',
    }

    if user_input.lower() == "exit":
        os._exit(0)

    tokens = user_input.split()
    if tokens:
        tokens[0] = tokens[0].lower()
        if tokens[0] == 'req':
            request['device_name'] = tokens[1]
            request['method'] = tokens[2]
        elif tokens[0] == 'list':
            request['method'] = tokens[0]
    try:
        jsonschema.validate(instance=request, schema=REQUEST_SCHEMA)
        return request
    except Exception:
        print("Invalid request")
        return None


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
                    os._exit(1)
                assert message is not None

                print('\r', message, end=f'\n{client.name} > ')

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
        client: Socket to send data to
    """
    while True:
        message: str = input(f'{client.name} > ')

        if message:
            to_send: Optional[dict] = parse_request(message)
            if to_send:
                assert to_send is not None
                client.send(to_send)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='rdfm-mgmt-shell server instance.',
        usage="""Documentation and list of commands:
        https://github.com/antmicro/rdfm/docs
        To exit just input "exit".""")
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the server')
    parser.add_argument('-port', metavar='p', type=int, default=1234,
                        help='listening port on the server')
    parser.add_argument('name', type=str,
                        help="""client name for identification,
                                without whitespaces""")
    parser.add_argument('-no_ssl', action='store_true',
                        help='turn off encryption')
    parser.add_argument('-cert', metavar='c', type=str,
                        default='./certs/CA.crt',
                        help="""CA cert file""")
    args = parser.parse_args()

    with open('json_schemas/request_schema.json', 'r') as f:
        REQUEST_SCHEMA = json.loads(f.read())

    client_socket: socket.socket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((args.hostname, args.port))
    if not args.no_ssl:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(args.cert)
        client_socket = context.wrap_socket(client_socket,
                                            server_hostname=args.hostname)

    # send registration
    client: Optional[Client] = create_client(CLIENT_TYPE, args.name,
                                             client_socket)
    assert client is not None
    client.send(client.registration_packet(args.name))

    t = Thread(target=recv_loop, args=(client,))
    t.start()
    send_loop(client)
