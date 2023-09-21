from typing import Optional
import os


""" Name of the environment variable providing the JWT secret """
ENV_TOKEN_NAME = "JWT_SECRET"


class ServerConfig():
    """ Server configuration
    """

    """ Hostname/IP address of the RDFM server

    Example: rdfm.example.com
             127.0.0.1
    """
    hostname: str

    """ Device socket port """
    port: int

    """ HTTP API port """
    http_port: int

    """ Should SSL be enabled for the API and device socket?
    """
    encrypted: bool

    """ Path to the server's CA Certificate, used only when SSL is enabled """
    cert: str

    """ Path to the server's private key, used only when SSL is enabled """
    key: str

    """ Database connection string """
    db_conn: str

    """ Path to the file transfer cache directory """
    cache_dir: str

    """ JWT secret key, do not expose this value anywhere! """
    jwt_secret: str

    """ Storage directory for packages when using (the default) local
        package driver
    """
    package_dir: str

    """ (DEBUG FLAG) Instruct the server to create mock data in the
        database when starting. DO NOT USE, for testing purposes only!
    """
    create_mocks: bool

    """ Enables server debug mode. This currently causes all requests
        to be logged to the server's stdout. DO NOT USE IN PRODUCTION!
    """
    debug: bool


def try_get_env(key: str,
                 help_text: str) -> Optional[str]:
    """ Wraps an environment variable read

    This function is a wrapper for environment variable reads.
    If the specified envvar does not exist, a user-friendly error
    message is printed indicating which environment variable is
    expected to be present.

    Args:
        key: environment variable name
        help_text: user friendly help text describing the variable

    Returns:
        None, if the environment variable is missing
        str,  the environment variable value if it exists
    """
    if key not in os.environ:
        print("Required environment variable missing:",
              key,
              f"({help_text})")
        return None
    return os.environ[key]


def parse_from_environment(config: ServerConfig) -> bool:
    """ Parses server configuration from the environment

    The passed `config` structure is updated with configuration
    values from the environment.

    Args:
        config: config structure to update with new values

    Returns:
        True,  if all required environment variables are present and
               have valid values
        False, if a required environment configuration variable was not
               provided, or it's value is invalid
    """
    jwt_secret = try_get_env(ENV_TOKEN_NAME, "JWT secret key")
    if jwt_secret is None:
        return False

    config.jwt_secret = jwt_secret
    return True
