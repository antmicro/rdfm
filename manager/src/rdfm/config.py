import argparse
from requests.auth import AuthBase
import typing

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

    """ Authorization object used to add auth data to the API requests
    """
    authorizer: typing.Type[AuthBase]
