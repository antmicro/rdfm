import os
import sys
from flask import (
    Flask,
    request
)
from threading import Thread
import server
import api.v1
import configuration


def add_debug_logging(app: Flask):
    """ Configure debug logging for all incoming requests
    """
    @app.before_request
    def before_request_func():
        if app.debug:
            print({
                'request': request,
                'form': request.form,
                'files': request.files
            }, file=sys.stderr)

    @app.after_request
    def after_request_func(response):
        response.direct_passthrough = True
        if app.debug:
            try:
                print({
                    'response': response.get_data(),
                    'status code': response.status
                }, file=sys.stderr)
            except Exception as e:
                print('Exception printing response'
                    'this can happen if it contains a file:', e)
        return response


def create_server_instance(config: configuration.ServerConfig) -> server.Server:
    """ Create static server data
    """
    try:
        srv = server.Server(config)
        if config.create_mocks:
            srv.create_mock_data()

        return srv
    except Exception as e:
        raise RuntimeError(f"Failed to connect to the database: {e}")


def create_app(config: configuration.ServerConfig) -> Flask:
    """ Create the Flask app object

    Create an app object with all API routes registered. The app
    is not yet runnable in this state, as further initialization
    is required (see: `setup`).
    """
    app = Flask(__name__)
    app.register_blueprint(api.v1.create_routes())
    app.config['RDFM_CONFIG'] = config
    if config.debug:
        add_debug_logging(app)
    return app


def setup(config: configuration.ServerConfig) -> Flask:
    """ Configure the Python environment for running the RDFM server

    Database and device management connections are tracked in a singleton
    `server.instance`. RDFM API methods import this singleton, which requires
    some setup before the Flask app can be run.
    This performs the required initialization of the `server.instance` global
    and creates an app object that can be safely run.
    """
    server.instance = create_server_instance(config)
    return create_app(config)


def setup_with_config_from_env() -> Flask:
    """ Create an RDFM server Flask app with configuration from environment only

    This factory utilizes only environment variables to configure the server.
    This can be used to run the server using a production WSGI server, where passing
    CLI flags is not possible.
    """
    config = configuration.ServerConfig()
    config.db_conn = os.getenv('RDFM_DB_CONNSTRING')
    config.package_dir = os.getenv('RDFM_LOCAL_PACKAGE_DIR')
    config.disable_api_auth = True if 'RDFM_DISABLE_API_AUTH' in os.environ else False
    if not configuration.parse_from_environment(config):
        raise RuntimeError("Parsing variables from the environment failed, cannot initialize app. "
                           "Please make sure all required environment variables are passed.")

    return setup(config)


def parse_config_from_cli() -> configuration.ServerConfig:
    """ Parse the server configuration from CLI arguments

    This is used only when starting the server from the CLI, when the
    development WSGI server (Werkzeug) is used.
    """
    import argparse

    config = configuration.ServerConfig()

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
    parser.add_argument('--no-api-auth', action='store_true',
                        dest='disable_api_auth',
                        help="disable API authentication")
    parser.add_argument('--test-mocks', action='store_true',
                        dest='create_mocks',
                        help="""insert mock data into the
                            database for running tests""")
    parser.add_argument('--debug', action='store_true',
                        help='launch server in debug mode')
    _ = parser.parse_args(namespace=config)

    return config


app: Flask = None


if __name__ == '__main__':
    config = parse_config_from_cli()
    # Environment parsing must come after the CLI flags,
    # as some environment variables depend on certain options.
    if not configuration.parse_from_environment(config):
        exit(1)

    try:
        app = setup(config)
    except Exception as e:
        print("RDFM server setup failed:", e)
        exit(1)

    print("Starting the RDFM HTTP API...")
    if config.encrypted:
        app.run(host=config.hostname, port=config.http_port,
                debug=config.debug, use_reloader=False,
                ssl_context=(config.cert, config.key))
    else:
        app.run(host=config.hostname, port=config.http_port,
                debug=config.debug, use_reloader=False)
