from requests.auth import AuthBase
from rdfm.config import Config
from authlib.integrations.requests_client import OAuth2Session
import requests
import typing


def make_rdfm_auth_header(token: str) -> str:
    """Creates an HTTP Authorization header for use with the RDFM API

    Args:
        token: management token received from the authorization server

    Returns:
        contents of the Authorization header to attach to the request
    """
    return f"Bearer token={token}"


class DefaultAuth(AuthBase):
    """Authorization stub for the RDFM API

    This is a dummy authorization generator to use when API auth is
    explicitly disabled in the manager configuration.
    """

    def __init__(self):
        pass

    def __call__(self, r):
        return r


class OAuth2ClientCredentials(AuthBase):
    """Authorization generator for accessing the RDFM API
        using OAuth2 Client Credentials grant.

    This requests a token from an external authorization server that
    will be used for authenticating requests made to the RDFM API.

    A configured client_id and client_secret is used for requesting
    a token using the Client Credentials OAuth2 grant.
    """

    client: OAuth2Session
    auth_url: str

    def __init__(self, config: Config):
        self.client = OAuth2Session(
            config.client_id, config.client_secret, scope=None
        )
        self.auth_url = config.auth_url

    def __call__(self, r: requests.Request):
        try:
            token = self.client.fetch_token(
                self.auth_url, grant_type="client_credentials"
            )
        except (requests.ConnectionError, requests.Timeout):
            print(
                "WARNING: Failed to connect to the authorization server at",
                self.auth_url,
            )
            raise

        # Extract the token from the response
        access_token = token["access_token"]
        r.headers["Authorization"] = make_rdfm_auth_header(access_token)
        return r


def create_authorizer(config: Config) -> typing.Type[AuthBase]:
    """Create an authorization object to be used with `requests` HTTP methods.

    This creates an object that adds authorization to all requests made by the
    manager. If no auth is configured, then no authorization will be added.

    Args:
        config: manager configuration
    """
    if not config.disable_api_auth:
        return OAuth2ClientCredentials(config)
    else:
        return DefaultAuth()
