
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
