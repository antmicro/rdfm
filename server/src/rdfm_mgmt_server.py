import os
from flask import (
    Flask,
)
from threading import Thread
import server
import api.v1

app = Flask(__name__)
app.register_blueprint(api.v1.create_routes())

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
                        help='server cert file')
    parser.add_argument('-key', type=str, default='./certs/SERVER.key',
                        help="""server cert key file""")
    parser.add_argument('-database', metavar='db', type=str,
                        default='sqlite:///devices.db',
                        help='database connection string')
    parser.add_argument('-cache_dir', type=str, default='server_file_cache',
                        help='file transfer cache directory')
    parser.add_argument('-jwt_secret', type=str,
                        default=os.environ['JWT_SECRET'],
                        help="""JWT secret key, if not provided it will
                            be read from $JWT_SECRET env var""")
    parser.add_argument('-test_mocks', action='store_true',
                        dest='create_mocks',
                        help="""insert mock data into the
                            database for running tests""")
    args = parser.parse_args()

    server.instance = server.Server(args.hostname, args.port,
                                    args.encrypted, args.cert, args.key,
                                    args.database, args.jwt_secret)
    if args.create_mocks:
        server.instance.create_mock_data()

    t = Thread(target=server.instance.run, daemon=True)
    t.start()

    if args.encrypted:
        app.config['UPLOAD_FOLDER'] = args.cache_dir
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False,
                ssl_context=(args.cert, args.key))
    else:
        app.run(host=args.hostname, port=args.http_port,
                debug=True, use_reloader=False)
