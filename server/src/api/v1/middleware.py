import datetime
import inspect
import functools
from marshmallow import ValidationError
import marshmallow_dataclass
from flask import request
from api.v1.common import api_error
import functools
from auth.device import decode_and_verify_token
from api.v1.common import api_error
from auth.device import DeviceToken
from flask import request
import time
import jwt
import traceback
import configuration
import requests
from typing import Callable, Optional, Any
from api.v1.common import api_error
from flask import request, current_app
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc6749.util import scope_to_list
import server


""" Read-write administrator scope """
SCOPE_READ_WRITE = 'rdfm_admin_rw'

""" Read-only administrator scope """
SCOPE_READ_ONLY = 'rdfm_admin_ro'

""" Text to append after the endpoint's docstring when a token
    with read-only scope is required
"""
DOCS_SCOPE_RO_TEXT = f"""
.. warning:: Accessing this endpoint requires providing a management token with read-only scope ``{SCOPE_READ_ONLY}`` or administrative scope ``{SCOPE_READ_WRITE}``.
"""

""" Text to append after the endpoint's docstring when a token
    with read-write scope is required
"""
DOCS_SCOPE_RW_TEXT = f"""
.. warning:: Accessing this endpoint requires providing a management token with read-write scope ``{SCOPE_READ_WRITE}``.
"""

""" Unprotected API routes
"""
DOCS_PUBLIC_API_TEXT = f"""
.. note:: This is a public API route; no authorization is required to access it.
"""

""" API routes requiring a device token
"""
DOCS_DEVICE_API_TEXT = f"""
.. warning:: Accessing this endpoint requires providing a device token.
"""


def __add_scope_docs(function, text: str):
    """ Add scope documentation to the specified function

    This function ensures that the passed in text has the same indentation
    level as the function's docstring, otherwise the docs are not properly
    generated.

    This assumes that the docs are indented with 4 spaces, similarly to
    this very docstring.
    """
    lines = text.splitlines()
    if function.__doc__ is not None:
        function.__doc__ += "\n"
        for line in lines:
            function.__doc__ += "    "
            function.__doc__ += line
            function.__doc__ += "\n"
        function.__doc__ += "\n"


def __introspect_and_validate_token(conf: configuration.ServerConfig, token: str) -> Optional[list[str]]:
    """ Introspect and validate the given token against a configured
        authorization server.

    This calls the Token Introspection endpoint to validate the given token.

    Args:
        conf: server configuration
        token: token string provided in the API request

    Returns:
        None, if the request to the authorization server fails
        None, if the token is not valid (field `active` is False)
        None, if the authorization server does not provide the scopes
              in the introspection response, even when the token is valid
              (theoretically an optional feature of the Token Introspection
              extension)
        list[str], if the token is valid. A list of token scopes is returned.
    """
    try:
        # Introspect the token
        client = OAuth2Session(conf.token_introspection_client_id,
                               conf.token_introspection_client_secret)
        resp: requests.models.Response = client.introspect_token(conf.token_introspection_url,
                                                                 token=token)
        if resp.status_code != 200:
            print("Error during token introspection: authorization server "
                  "responded with a non-success status.", flush=True)
            return None

        introspected_token = resp.json()
        active = introspected_token['active']
        if not active:
            return None

        # According to the spec, the authorization server is allowed
        # to only return an `"active": True` response for valid tokens.
        if 'scope' not in introspected_token:
            print("Error during token introspection: authorization server "
                  "response did not contain a `scope` field for valid token. ",
                  flush=True)
            return None

        return scope_to_list(introspected_token['scope'])
    except Exception as e:
        print("Exception during token introspection:", e)
        return None


def deserialize_schema(schema_dataclass: type, key: str = 'payload'):
    """ Validate and deserialize the incoming request against a predefined marshmallow schema.

    This decorator verifies whether an incoming request's schema matches the
    one specified in the given schema, and deserializes it into the specified
    dataclass.

    If an invalid request schema was provided, the request handling will
    immediately terminate by returning an API error and the 400 status code.

    Args:
        schema_dataclass: dataclass representing the request schema, which the
                          request will be deserialized to.
        key: argument name for the deserialized structure. The receiving argument
             must be of the type as specified in `schema_dataclass`.
    """
    def _deserialize(f):
        @functools.wraps(f)
        def __deserialize(*args, **kwargs):
            if not hasattr(schema_dataclass, 'Schema'):
                raise RuntimeError("deserialize_schema requires a dataclass decorated "
                                   "with the @marshmallow_dataclass.dataclass decorator")

            try:
                payload: schema_dataclass = schema_dataclass.Schema().load(request.json)
            except ValidationError as e:
                return api_error(f"schema validation failed: {e.messages}", 400)

            spec = inspect.getfullargspec(f)
            if key in kwargs:
                raise RuntimeError("deserialize_schema decorator was used, but the wrapped route function "
                                   f"<{f.__name__}> "
                                   f"is already receiving an argument with the name: <{key}>")
            if key not in spec.args:
                raise KeyError("deserialize_schema decorator was used, but the wrapped route function "
                               f"<{f.__name__}> "
                               "does not accept the deserialized structure parameter "
                               f"(missing function argument: <{key}> of type: <{schema_dataclass.__name__}>)")

            kwargs[key] = payload
            return f(*args, **kwargs)
        return __deserialize

    return _deserialize


def device_api(f):
    """ Decorator for device APIs

    This decorator verifies whether an incoming request contains a valid
    device token. If no token was provided, or an invalid/expired one
    was given, the request handling will immediately terminate by
    returning an API error and 401 Unauthorized status code.
    """
    f.__rdfm_api_privileges__ = "device"
    __add_scope_docs(f, DOCS_DEVICE_API_TEXT)

    @functools.wraps(f)
    def _device_api(*args, **kwargs):
        auth = request.authorization
        if auth is None:
            return api_error("no Authorization header was provided", 401)
        if auth.type != "bearer":
            return api_error("invalid authorization - expected authorization type Bearer", 401)
        if "token" not in auth:
            return api_error("invalid authorization - missing field: token")

        token = decode_and_verify_token(auth["token"])
        if token is None:
            return api_error("invalid token was provided", 401)

        # Update the last accessed timestamp for this device
        try:
            server.instance._devices_db.update_timestamp(token.device_id, datetime.datetime.utcnow())
        except Exception as e:
            print(f"Failed to update timestamp for device {token.device_id}, exception: {e}", flush=True)

        kwargs["device_token"] = token
        return f(*args, **kwargs)
    return _device_api


def __management_api(scope_check_callback: Callable[[list[str]], bool]):
    """ Decorator for management APIs

    This decorator verifies whether an incoming request contains a valid
    management token. If no token was provided, or an invalid/expired one
    was given, the request handling will immediately terminate by
    returning an API error and 401 Unauthorized status code.
    If a valid token is present, the claims of the token are checked for
    the provided required scopes. If any of the scopes are missing, request
    handling will immediately terminate returning an API error and
    403 Forbidden status code.

    Args:
        scope_check_callback: callback that is called with the list of scopes contained
                              within the token. If the client should not be authorized,
                              the callback is expected to return False. Otherwise, True
                              will allow the request to be processed.
    """
    def _management_api_impl(f):
        @functools.wraps(f)
        def __management_api_impl(*args, **kwargs):
            # First, check if authentication was not explicitly disabled
            conf: configuration.ServerConfig = current_app.config['RDFM_CONFIG']
            if conf.disable_api_auth:
                return f(*args, **kwargs)

            # Extract token from the Authorization header
            auth = request.authorization
            if auth is None:
                return api_error("no Authorization header was provided", 401)
            if auth.type != "bearer":
                return api_error("invalid authorization - expected authorization type Bearer", 401)
            if "token" not in auth:
                return api_error("invalid authorization - missing field: token", 401)
            token: str = auth["token"]

            scopes: Optional[list[str]] = __introspect_and_validate_token(conf, token)
            if scopes is None:
                return api_error("unauthorized", 401)

            if not scope_check_callback(scopes):
                print("Rejecting request - authenticated user does not "
                      "have the required scopes to access this resource "
                      f"(user claims: {', '.join(scopes)})", flush=True)
                return api_error("accessing this resource requires OAuth2 scopes "
                                 "which are not provided by the authenticated client", 403)

            # Verified the token successfully, the user is authorized
            # Call the original view function
            return f(*args, **kwargs)
        return __management_api_impl
    return _management_api_impl


def management_read_only_api(f):
    """ Decorator to be used on read-only management API routes

    This decorator verifies if the requester has read-only access
    to the protected resource.
    """
    client_has_ro_scope = lambda scopes: SCOPE_READ_ONLY in scopes
    client_has_rw_scope = lambda scopes: SCOPE_READ_WRITE in scopes
    client_read_allowed = lambda scopes: client_has_ro_scope(scopes) or client_has_rw_scope(scopes)

    # Mark the handler function with a custom attribute
    f.__rdfm_api_privileges__ = "management_ro"
    __add_scope_docs(f, DOCS_SCOPE_RO_TEXT)

    return __management_api(client_read_allowed)(f)


def management_read_write_api(f):
    """ Decorator to be used on read-write management API routes

    This decorator verifies if the requester has read-write access to the protected
    """
    client_has_rw_scope = lambda scopes: SCOPE_READ_WRITE in scopes

    # Mark the handler function with a custom attribute
    f.__rdfm_api_privileges__ = "management_rw"
    __add_scope_docs(f, DOCS_SCOPE_RW_TEXT)

    return __management_api(client_has_rw_scope)(f)


def public_api(f):
    """ Decorator to be used on public API routes

    These routes do not require authorization. This should be used with caution.
    """
    f.__rdfm_api_privileges__ = "public"
    __add_scope_docs(f, DOCS_PUBLIC_API_TEXT)
    return f
