import socket
import errno
import sys
import jsonschema
from threading import Thread

from communication import *

REQUEST_SCHEMA = {}


def parse_request(user_input: str) -> dict:
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

    tokens = user_input.split()
    if tokens:
        tokens[0] = tokens[0].lower()
        if tokens[0] == 'req':
            request['device_name'] = tokens[1]
            request['method'] = tokens[2]
        elif tokens[0] == 'list':
            request['method'] = tokens[0]

    jsonschema.validate(instance=request, schema=REQUEST_SCHEMA)
    return request


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
                    print('client response:', client_response)
                    client.send(client_response)

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
        server: Listening server socket
    """
    while True:
        message = input(f'{client.name} > ')

        if message:
            client.send(parse_request(message))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='rdfm-mgmt-shell server instance.')
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the server')
    parser.add_argument('-port', metavar='p', type=int, default=1234,
                        help='listening port on the server')
    parser.add_argument('client_type', type=str.upper,
                        choices=['USER', 'DEVICE'],
                        help='client type')
    parser.add_argument('name', type=str,
                        help="""client name for identification,
                                without whitespaces""")
    parser.add_argument('-file', metavar='f', type=str, default='',
                        help='file containing device metadata')
    args = parser.parse_args()

    with open('json_schemas/request_schema.json', 'r') as f:
        REQUEST_SCHEMA = json.loads(f.read())

    client_socket: socket.socket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((args.hostname, args.port))

    # send registration
    client: Optional[Client] = create_client(
        args.client_type, args.name, client_socket)
    assert client is not None
    if isinstance(client, Device):
        client.metadata_file = args.file
    client.send(client.registration_packet(args.client_type, args.name))

    t = Thread(target=recv_loop, args=(client,))
    t.start()
    send_loop(client)
