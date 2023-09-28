import argparse
from requests.auth import AuthBase
import typing
import os.path
import json


MANAGER_CONFIG_DEFAULT = "~/.config/rdfm-mgmt/config.json"


class Config():
    """ Contains configuration fields for the manager utility
    """

    """ URL pointing to the RDFM Management Server

    Example: https://rdfm.example.com/
             https://rdfm.example.com:5000/
    """
    server_url: str

    """ Path to the server CA certificate used for verifying the HTTPS connection
    """
    ca_cert: str

    """ Disables authentication for requests made to the RDFM server
    """
    disable_api_auth: bool

    """ URL to the authorization server to use for acquiring a
        management token
    """
    auth_url: str

    """ Client ID to use for OAuth2 Client Credentials authentication
    """
    client_id: str

    """ Client secret to use for OAuth2 Client Credentials authentication
    """
    client_secret: str

    """ Authorization object used to add auth data to the API requests
    """
    authorizer: typing.Type[AuthBase]


def try_get_config(dict: dict[str, typing.Any],
                   key: str,
                   help_text: str) -> typing.Optional[typing.Any]:
    """ Try getting a value from a config dictionary

    If the specified key is not present, a user-friendly error is printed.

    Args:
        dict: dictionary to read from
        key: key in the dictionary
        help_text: explanation of the key
    """
    if key not in dict:
        print("Configuration file is missing a setting:", key, f"({help_text})")
        return None
    return dict[key]



def load_auth_from_file(config: Config, path: str = MANAGER_CONFIG_DEFAULT):
    """ Load auth configuration from a file.

    This loads configuration fields relating to API authentication
    from a local file. The passed in config structure is updated
    with the loaded values.

    Args:
        config: configuration structure to fill in
        path: path to the configuration file
    """
    # If authentication is disabled, we don't need to do anything else
    if config.disable_api_auth:
        return

    # Expand the path to the user's home directory
    expanded_path = os.path.expanduser(path)
    if not os.path.isfile(expanded_path):
        raise RuntimeError(f"Authorization is enabled, but config file does not exist: {expanded_path}")

    # Load config from file
    try:
        with open(expanded_path, 'rt') as f:
            contents = f.read()

        values = json.loads(contents)
        auth_url: typing.Optional[str] = try_get_config(values, 'auth_url', 'Authorization server URL')
        client_id: typing.Optional[str] = try_get_config(values, 'client_id', 'Authorization Client Identifier')
        client_secret: typing.Optional[str] = try_get_config(values, 'client_secret', 'Authorization Client Secret')
        if None in [auth_url, client_id, client_secret]:
            raise RuntimeError("Missing authorization configuration variables")

        config.auth_url = auth_url
        config.client_id = client_id
        config.client_secret = client_secret
    except Exception as e:
        raise RuntimeError(f"Could not read from config file {expanded_path}: {e}")
