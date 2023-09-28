from typing import Optional
from http.client import responses
import rdfm.config
import urllib.parse
import requests
from rdfm.schema.v1.error import ApiError


def escape(config: rdfm.config.Config, path: str) -> str:
    """ Wrapper to properly escape the path part of a constructed API URL
    """
    return urllib.parse.urljoin(config.server_url,
                                urllib.parse.quote(path))


def wrap_api_error(response: requests.Response, prefix: str) -> Optional[str]:
    """ Wrapper for common response status codes

    Args:
        response: response object for the request
        prefix: prefix to add to the error message

    Returns:
        None, if the operation was successful
        str, if the operation failed in some way
    """
    msg = ""
    match response.status_code:
        case 200:
            # We must return None here, as this is not an error condition
            return None
        case 400:
            msg = "Bad request, you may have provided invalid data"
            try:
                msg += f" (server says: {response.json()['error']})"
            except:
                msg += " (could not retrieve response error string)"
        case 401:
            msg = "Unauthorized to access the server"
        case 403:
            msg = ("Unauthorized to perform the specified operation. "
                   "Your credentials do not have sufficient privileges "
                   "(most likely, trying to access read-write APIs using "
                   "a read-only user)")
        case 404:
            msg = "Resource not found"
        case 500:
            try:
                error: ApiError = ApiError.Schema().load(response.json())
                msg = f'Internal server error (server says: {error})'
            except:
                msg = "Internal server error (unknown)"
        case _:
            msg = "Unexpected status received from the server" \
                  f"({response.status_code} - {responses[response.status_code]})"
    return f"{prefix}: {msg}"

