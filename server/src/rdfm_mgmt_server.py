import os
from flask import (
    Flask,
    request
)
from threading import Thread
import server
import api.v1
import configuration

app = Flask(__name__)
app.register_blueprint(api.v1.create_routes())

@app.before_request
def before_request_func():
    if app.debug:
        print({
            'request': request,
            'form': request.form,
            'files': request.files
        })


@app.after_request
def after_request_func(response):
    response.direct_passthrough = True
    if app.debug:
        try:
            print({
                'response': response.get_data(),
                'status code': response.status
            })
        except Exception as e:
            print('Exception printing response'
                  'this can happen if it contains a file:', e)
    return response

if __name__ == '__main__':
    import argparse

    config = configuration.ServerConfig()
    if not configuration.parse_from_environment(config):
        exit(1)

    parser = argparse.ArgumentParser(
        description='RDFM management server instance.')
    # Note: all configuration variables should be stored in the
    # in the `configuration.ServerConfig` struct, to allow for
    # alternate configuration storage methods (file, CLI, etc.).
    # For simplicity, the arguments from the CLI are parsed directly
    # into the config struct above.
    # This requires that the names of the configuration variables match
    # the CLI argument name. Use `dest='<name>'` in calls to `add_argument`
    # for cases where this is not desirable.
    parser.add_argument('--hostname', type=str, default='127.0.0.1',
                        help='ip addr or domain name of the host')
    parser.add_argument('--port', metavar='p', type=int, default=1234,
                        help='listening port')
    parser.add_argument('--http-port', metavar='hp', type=int, default=5000,
                        help='listening port')
    parser.add_argument('--no-ssl', action='store_false', dest='encrypted',
                        help='turn off encryption')
    parser.add_argument('--cert', type=str, default='./certs/SERVER.crt',
                        help='server cert file')
    parser.add_argument('--key', type=str, default='./certs/SERVER.key',
                        help="""server cert key file""")
    parser.add_argument('--database', metavar='db', type=str, dest='db_conn',
                        default='sqlite:///devices.db',
                        help='database connection string')
    parser.add_argument('--cache-dir', type=str, default='server_file_cache',
                        help='file transfer cache directory')
    parser.add_argument('--local-package-dir', type=str, dest='package_dir',
                        default='/tmp/.rdfm-local-storage/',
                        help='package storage directory')
    parser.add_argument('--test-mocks', action='store_true',
                        dest='create_mocks',
                        help="""insert mock data into the
                            database for running tests""")
    parser.add_argument('--debug', action='store_true',
                        help='launch server in debug mode')
    args = parser.parse_args(namespace=config)

    print("Starting the RDFM device socket listener...")
    try:
        server.instance = server.Server(config)
        if config.create_mocks:
            server.instance.create_mock_data()
        t = Thread(target=server.instance.run, daemon=True)
        t.start()
    except Exception as e:
        print("Failed to start RDFM device socket listener:", e)
        exit(1)

    print("Starting the RDFM HTTP API...")
    app.config['RDFM_CONFIG'] = config
    if config.encrypted:
        app.run(host=config.hostname, port=config.http_port,
                debug=config.debug, use_reloader=False,
                ssl_context=(config.cert, config.key))
    else:
        app.run(host=config.hostname, port=config.http_port,
                debug=config.debug, use_reloader=False)
