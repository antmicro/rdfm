from flask import Flask
from threading import Thread
from server import Server
from request_models import (
    ListRequest,
    InfoDeviceRequest,
    UpdateDeviceRequest,
    ProxyDeviceRequest
)

app = Flask(__name__)


@app.route('/')
def index():
    response = server.handle_request(ListRequest())
    assert response is not None
    return response.json()


@app.route('/device/<device_name>', methods=['GET'])
def device_metadata(device_name: str):
    response = server.handle_request(
        InfoDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.json()


@app.route('/device/<device_name>/update')
def device_update(device_name: str):
    response = server.handle_request(
        UpdateDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.json()


@app.route('/device/<device_name>/proxy')
def device_proxy(device_name: str):
    response = server.handle_request(
        ProxyDeviceRequest(device_name=device_name)  # type: ignore
    )
    assert response is not None
    return response.json()


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
    parser.add_argument('-database', metavar='db', type=str,
                        default='devices.db',
                        help='filepath to store device database')
    args = parser.parse_args()

    server = Server(args.hostname, args.port,
                    args.encrypted, args.cert, args.key,
                    args.database)
    t = Thread(target=server.run, daemon=True)
    t.start()

    if args.encrypted:
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False,
                ssl_context=(args.cert, args.key))
    else:
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False)
