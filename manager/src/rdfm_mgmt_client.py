import socket
import errno
import sys
import os
import base64
import urllib.parse
import ssl
import base64
from math import ceil
from typing import Optional
from threading import Thread
from rdfm_mgmt_communication import (
    Client,
    User,
    create_client
)
from request_models import (
    Container,
    Request,
    ClientGroups,
    ClientRequest,
    RegisterRequest,
    SendFileRequest,
    FileCompletedRequest,
    UploadDeviceRequest
)


def user_cmd_to_request(user_input: str) -> Optional[Request]:
    """Parses user input to the request

    Args:
        user_input: Input received from the user shell
        example: "REQ d1 proxy"

    Returns:
        Parsed user request
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
            if tokens[2] == 'download':
                request['file_path'] = tokens[3]
            if tokens[2] == 'upload':
                request['file_path'] = tokens[3]
                request['src_file_path'] = tokens[4]
        elif tokens[0] == 'list':
            request['method'] = tokens[0]

    try:
        parsed_request = Container.model_validate({'data': request}).data
        assert isinstance(parsed_request, Request)
        return parsed_request
    except Exception:
        print("Invalid request")
        return None


def recv_loop(client: User) -> None:
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
                request: Optional[Request] = client.receive()
                if request is None:
                    # server closed
                    print('Connection closed by the server')
                    os._exit(1)
                assert request is not None
                match request:
                    case SendFileRequest():
                        download_file_part(client, request)
                    case _:
                        client.prompt(str(request.model_dump_json()))

        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Reading error: {}'.format(str(e)))
                sys.exit()

        except Exception as e:
            print('Reading error: ', e)
            sys.exit()


def send_loop(client: User) -> None:
    """Send messages to the server

    Args:
        client: Client connected to the server
    """
    while True:
        cmd: str = input(f'{client.name} > ')

        if cmd:
            to_send: Optional[Request] = user_cmd_to_request(cmd)
            if to_send:
                assert to_send is not None
                client.send(to_send)
                if isinstance(to_send, UploadDeviceRequest):
                    src_file_path = to_send.src_file_path
                    upload_file(client, to_send.file_path, src_file_path)


def download_file_part(client: User, request: SendFileRequest) -> None:
    """Download file part

    Args:
        client: Client connected to the server
        request: Request containing file part received from server
    """
    try:
        file_name = os.path.basename(request.file_path)
        write_mode = 'ab'
        if request.part == 1:
            client.prompt(f'Started downloading file {request.file_path}')
            write_mode = 'wb'
        with open(file_name, write_mode) as f:
            f.write(base64.urlsafe_b64decode(
                urllib.parse.unquote(request.content)
            ))
        if request.part == request.parts_total:
            client.prompt(f'{request.file_path} downloaded')
            client.send(
                FileCompletedRequest(  # type: ignore
                    file_path=request.file_path
                )
            )
    except Exception as e:
        client.prompt(f'Couldn\'t receive {file_name}, {e}')


def upload_file(client: User, file_path: str, src_file_path: str) -> None:
    """Send file to the server that will forward it to the device
    Device that will receive file was specified in 'upload' request
    that serves as a file transfer register packet

    Args:
        client: Client connected to the server
        file_path: Path where to upload file on device
        src_file_path: Path of the file to send
    """

    BUFSIZE = 16384
    bytes_to_send = os.path.getsize(src_file_path)
    parts_to_send = ceil(bytes_to_send / BUFSIZE)

    try:
        with open(src_file_path, "rb") as f:
            for i in range(1, parts_to_send+1):
                buf = f.read(min(bytes_to_send, BUFSIZE))
                bytes_to_send -= len(buf)

                client.send(SendFileRequest(  # type: ignore
                    part=i,
                    parts_total=parts_to_send,
                    file_path=file_path,
                    content=base64.standard_b64encode(buf).decode(),
                ))
        print("File uploaded")
    except Exception as e:
        client.prompt(f'Exception thrown while uploading file, {str(e)}')


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

    client_socket: socket.socket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((args.hostname, args.port))
    if not args.no_ssl:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(args.cert)
        client_socket = context.wrap_socket(client_socket,
                                            server_hostname=args.hostname)

    # send registration
    client: Optional[Client] = create_client(ClientGroups.USER, args.name,
                                             client_socket, None)
    assert client is not None
    assert isinstance(client, User)
    reg_req = RegisterRequest(client=ClientRequest(  # type: ignore
        group=ClientGroups.USER,
        name=args.name
    ))
    client.send(reg_req)

    t = Thread(target=recv_loop, args=(client,))
    t.start()
    send_loop(client)
