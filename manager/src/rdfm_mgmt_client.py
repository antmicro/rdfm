import argparse
import socket
import errno
import sys
import os
import ssl
import requests
from typing import Optional
from threading import Thread
from rdfm_mgmt_communication import (
    Client,
    User,
    create_client,
)
from request_models import (
    Container,
    Request,
    ClientGroups,
    ClientRequest,
    RegisterRequest,
    UploadDeviceRequest,
    DownloadDeviceRequest,
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

    try:
        tokens = user_input.split()
        if tokens:
            tokens[0] = tokens[0].lower()
            if tokens[0] == 'req':
                request['device_name'] = tokens[1]
                request['method'] = tokens[2]
                if tokens[2] == 'download':
                    request['file_path'] = tokens[3]
                    if len(tokens) > 4:
                        request['dst_file_path'] = tokens[4]
                    else:
                        request['dst_file_path'] = os.path.basename(
                                                        request['file_path'])
                if tokens[2] == 'upload':
                    request['file_path'] = tokens[3]
                    request['src_file_path'] = tokens[4]
            elif tokens[0] == 'list':
                request['method'] = tokens[0]

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
                client.prompt(str(request.model_dump_json()))

        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Reading error: {}'.format(str(e)))
                sys.exit()

        except Exception as e:
            print('Reading error: ', e)
            sys.exit()


def send_upload_request(request: UploadDeviceRequest,
                        args) -> requests.Response:
    """Sends upload request via server file transfer API

    Args:
        request: Request parsed from client cmd
        args: Client program args

    Returns:
        server response
    """
    to_send = {
        'url': f'{args.files_url}/device/{request.device_name}/upload',
        'data': {
            'file_path': request.file_path
        },
        'files': {
            'file': open(request.src_file_path),
        }
    }
    if args.files_url.startswith('https'):
        to_send['verify'] = args.cert
    res = requests.post(**to_send)  # type: ignore
    return res


def send_download_request(request: DownloadDeviceRequest,
                          args) -> int:
    """Sends download request via server file transfer API

    Args:
        request: Request parsed from client cmd
        args: Client program args

    Returns:
        response status code
    """
    to_send = {
        'url': f'{args.files_url}/device/{request.device_name}/download',
        'data': {
            'file_path': request.file_path
        }
    }
    if args.files_url.startswith('https'):
        to_send['verify'] = args.cert
    res = requests.get(**to_send)  # type: ignore
    with open(request.dst_file_path, 'wb') as f:
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return res.status_code


def send_loop(client: User, args) -> None:
    """Send messages to the server

    Args:
        client: Client connected to the server
        args: Client program args
    """
    while True:
        cmd: str = input(f'{client.name} > ')

        if cmd:
            to_send: Optional[Request] = user_cmd_to_request(cmd)
            if to_send:
                assert to_send is not None
                client.send(to_send)
                if isinstance(to_send, UploadDeviceRequest):
                    print("Uploading file...")
                    res = send_upload_request(to_send, args)
                    if res:
                        print(res)
                if isinstance(to_send, DownloadDeviceRequest):
                    print("Downloading file...")
                    res_status_code = send_download_request(to_send, args)
                    if res_status_code:
                        print(res_status_code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='rdfm-mgmt-shell server instance.',
        usage="""Documentation and list of commands:
        https://github.com/antmicro/rdfm/docs
        To exit just input "exit".""")
    parser.add_argument('-hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the server')
    parser.add_argument('-files_url', type=str,
                        default='https://127.0.0.1:5000/',
                        help='url of file transfer api')
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
    send_loop(client, args)
