from typing import Optional
import os


""" Name of the environment variable providing the JWT secret """
ENV_TOKEN_NAME = "JWT_SECRET"
""" Configuration for the storage type """
ENV_STORAGE_DRIVER = "RDFM_STORAGE_DRIVER"
""" S3-specific environment variables """
ENV_S3_URL = "RDFM_S3_URL"
ENV_S3_ACCESS_KEY_ID = "RDFM_S3_ACCESS_KEY_ID"
ENV_S3_SECRET_ACCESS_KEY = "RDFM_S3_ACCESS_SECRET_KEY"
ENV_S3_USE_V4_SIGNATURE = "RDFM_S3_USE_V4_SIGNATURE"
ENV_S3_REGION_NAME = "RDFM_S3_REGION_NAME"
ENV_S3_BUCKET = "RDFM_S3_BUCKET"
""" List of valid storage types for packages that the server supports.
    These values should match the ones found in`storage.driver_by_name`.
"""
ALLOWED_STORAGE_DRIVERS = ["local", "s3"]

ENV_OAUTH_URL = "RDFM_OAUTH_URL"
ENV_OAUTH_CLIENT_ID = "RDFM_OAUTH_CLIENT_ID"
ENV_OAUTH_CLIENT_SECRET = "RDFM_OAUTH_CLIENT_SEC"

ENV_HOSTNAME = "RDFM_HOSTNAME"
ENV_API_PORT = "RDFM_API_PORT"

ENV_FRONTEND_APP_URL = "RDFM_FRONTEND_APP_URL"
ENV_INCLUDE_FRONTEND_ENDPOINT = "RDFM_INCLUDE_FRONTEND_ENDPOINT"


class ServerConfig:
    """Server configuration"""

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

    """ Storage driver to use
    """
    storage_driver: str

    """ Override the default S3 endpoint URL

    This allows to override the default S3 endpoint when using an alternate
    S3-compatible object storage (for example, MinIO).
    """
    s3_url: Optional[str]

    """ Access Key ID for storing packages on S3
    """
    s3_access_key_id: Optional[str]

    """ Secret Access Key for storing packages on S3
    """
    s3_secret_access_key: Optional[str]

    """ Bucket name for storing packages on S3
    """
    s3_bucket_name: Optional[str]

    """ Should Signature Version 4 Authentication be used for S3 access?
    """
    s3_use_v4_signature: Optional[bool]

    """ Name of the region in which the S3 bucket is located
    """
    s3_region_name: Optional[str]

    """ Should API auth be disabled?
        WARNING: This disables ALL authentication on the exposed API.
        DO NOT USE OUTSIDE A DEVELOPMENT ENVIRONMENT!
    """
    disable_api_auth: bool

    """ URL to OAuth2 login endpoint.
        This is used to redirect user to the OAuth2 login page
        to authenticate.
    """
    oauth_login_url: str

    """ URL to OAuth2 logout endpoint.
        This is used to redirect user to the OAuth2 logout page
        to de-authenticate and clear the session.
    """
    oauth_logout_url: str

    """ URL to the frontend application
        This is used for authentication handling and redirection
        after login/logout. If the frontend application is not server
        on a dedicated endpoint, this value is not used.
    """
    frontend_app_url: str

    """ URL to an RFC 7662-compatible OAuth2 Token Introspection endpoint.
        This is used to validate tokens from requests coming to the server API.
    """
    token_introspection_url: str

    """ When authentication is required to access token introspection,
        this defines the client_id that will be attached in the
        basic authorization header when making an introspection
        request.
    """
    token_introspection_client_id: str

    """ When authentication is required to access token introspection,
        this defines the client_secret that will be attached in the
        basic authorization header when making an introspection
        request.
    """
    token_introspection_client_secret: str

    """ (DEBUG FLAG) Instruct the server to create mock data in the
        database when starting. DO NOT USE, for testing purposes only!
    """
    create_mocks: bool = False

    """ Enables server debug mode. This currently causes all requests
        to be logged to the server's stdout. DO NOT USE IN PRODUCTION!
    """
    debug: bool = False

    """ Determines whether frontend application should be served on
        a dedicated endpoint.
    """
    include_frontend: bool = False

    """ Disables CORS checks for development purposes
        DO NOT USE OUTSIDE A DEVELOPMENT ENVIRONMENT!
    """
    disable_cors: bool = False


def try_get_env(key: str, help_text: str) -> Optional[str]:
    """Wraps an environment variable read

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
        print("Required environment variable missing:", key, f"({help_text})")
        return None
    return os.environ[key]


def parse_from_environment(config: ServerConfig) -> bool:
    """Parses server configuration from the environment

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

    if not hasattr(config, "hostname"):
        if (hostname := try_get_env(ENV_HOSTNAME, "Hostname")) is None:
            return False
        config.hostname = hostname

    if not hasattr(config, "http_port"):
        if (http_port := try_get_env(ENV_API_PORT, "HTTP API port")) is None:
            return False
        try:
            config.http_port = int(http_port)
        except ValueError:
            print(f"Invalid port specified: {http_port}")
            return False

    config.storage_driver = os.environ.get(ENV_STORAGE_DRIVER, "local")
    if config.storage_driver not in ALLOWED_STORAGE_DRIVERS:
        print(
            "Invalid storage driver: got",
            config.storage_driver,
            " expected one of:",
            ALLOWED_STORAGE_DRIVERS,
        )
        return False

    if config.storage_driver == "s3":
        config.s3_url = os.environ.get(ENV_S3_URL, None)
        config.s3_use_v4_signature = (
            os.environ.get(ENV_S3_USE_V4_SIGNATURE, "False").lower() == "true"
        )
        config.s3_region_name = os.environ.get(ENV_S3_REGION_NAME, None)

        config.s3_access_key_id = try_get_env(
            ENV_S3_ACCESS_KEY_ID, "S3 Access Key ID"
        )
        config.s3_secret_access_key = try_get_env(
            ENV_S3_SECRET_ACCESS_KEY, "S3 Secret Access Key"
        )
        config.s3_bucket_name = try_get_env(ENV_S3_BUCKET, "S3 Bucket name")
        if None in [
            config.s3_access_key_id,
            config.s3_secret_access_key,
            config.s3_bucket_name,
        ]:
            return False

    if config.disable_cors and config.include_frontend:
        print("Cannot disable CORS and include the frontend application " +
              "at the same time.")
        return False

    if not config.include_frontend:
        if ENV_FRONTEND_APP_URL not in os.environ:
            print(f"Environment variable missing: {ENV_FRONTEND_APP_URL}, " +
                  "this is required in order to use the frontend application")
            config.frontend_app_url = None
        else:
            config.frontend_app_url = os.environ[ENV_FRONTEND_APP_URL]

    # Token Introspection variables are only required when running
    # with authentication enabled.
    if not config.disable_api_auth:
        oauth_url = try_get_env(
            ENV_OAUTH_URL, "RFC 7662 Token Introspection endpoint"
        )
        oauth_client_id = try_get_env(
            ENV_OAUTH_CLIENT_ID,
            "OAuth2 client_id to authenticate introspection requests",
        )
        oauth_client_secret = try_get_env(
            ENV_OAUTH_CLIENT_SECRET,
            "OAuth2 client_secret to authenticate introspection requests",
        )
        if None in [
            oauth_url,
            oauth_client_id,
            oauth_client_secret,
        ]:
            return False
        else:
            config.token_introspection_url = str(oauth_url)
            config.token_introspection_client_id = str(oauth_client_id)
            config.token_introspection_client_secret = str(oauth_client_secret)
    return True
