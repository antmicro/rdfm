import datetime
import inspect
import functools
from marshmallow import ValidationError
from flask import request, current_app, Response
from api.v1.common import api_error
from auth.device import decode_and_verify_token
import configuration
import requests
from typing import Callable, Optional
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc6749.util import scope_to_list
import server
from simple_websocket import Server, ConnectionClosed
from rdfm.ws import WebSocketException
from device_mgmt.helpers import WS_PING_INTERVAL


""" Read-write administrator scope """
SCOPE_READ_WRITE = "rdfm_admin_rw"

""" Read-only administrator scope """
SCOPE_READ_ONLY = "rdfm_admin_ro"

""" Single file package write scope """
SCOPE_SINGLE_FILE = "rdfm_upload_single_file"

""" Rootfs Image package write scope """
SCOPE_ROOTFS_IMAGE = "rdfm_upload_rootfs_image"

""" Text to append after the endpoint's docstring when an appropriate
    package write scope is required
"""
DOCS_SCOPE_PACKAGE_TEXT = \
    """.. warning:: Accessing this endpoint requires """ \
    """providing a management token with the appropriate """ \
    """package write scope. Available scopes are: """ \
    f"""``{SCOPE_SINGLE_FILE}`` - single file package, """ \
    f"""``{SCOPE_ROOTFS_IMAGE}`` - rootfs image package.""" \
    f"""``{SCOPE_READ_WRITE}`` - all package write scopes."""

""" Text to append after the endpoint's docstring when a token
    with read-only scope is required
"""
DOCS_SCOPE_RO_TEXT = """.. warning:: Accessing this endpoint requires """ \
                     """providing a management token with read-only scope """ \
                     f"""``{SCOPE_READ_ONLY}`` or administrative scope """ \
                     f"""``{SCOPE_READ_WRITE}``."""

""" Text to append after the endpoint's docstring when a token
    with read-write scope is required
"""
DOCS_SCOPE_RW_TEXT = """.. warning:: Accessing this endpoint requires """ \
                     """providing a management token with read-write scope""" \
                     f""" ``{SCOPE_READ_WRITE}``."""

""" Unprotected API routes
"""
DOCS_PUBLIC_API_TEXT = """.. note:: This is a public API route; no """ \
                       """authorization is required to access it."""

""" API routes requiring a device token
"""
DOCS_DEVICE_API_TEXT = """
.. warning:: Accessing this endpoint requires providing a device token.
"""

""" WebSocket routes
"""
DOCS_WEBSOCKET_ROUTE = """
.. note:: This is a WebSocket route.
"""


def __add_scope_docs(function, text: str):
    """Add scope documentation to the specified function

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


def __introspect_and_validate_token(
    conf: configuration.ServerConfig, token: str
) -> Optional[list[str]]:
    """Introspect and validate the given token against a configured
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
        client = OAuth2Session(
            conf.token_introspection_client_id,
            conf.token_introspection_client_secret,
        )
        resp: requests.models.Response = client.introspect_token(
            conf.token_introspection_url, token=token
        )
        if resp.status_code != 200:
            print(
                "Error during token introspection: authorization server "
                "responded with a non-success status.",
                flush=True,
            )
            return None

        introspected_token = resp.json()

        active = introspected_token["active"]
        if not active:
            return None

        # According to the spec, the authorization server is allowed
        # to only return an `"active": True` response for valid tokens.
        if "scope" not in introspected_token:
            print(
                "Error during token introspection: authorization server "
                "response did not contain a `scope` field for valid token. ",
                flush=True,
            )
            return None

        scopes = scope_to_list(introspected_token["scope"])

        # Keycloak specific, extracts roles from the user's
        # access token and adds them to the list of scopes
        if (
            "realm_access" in introspected_token and
            "roles" in introspected_token["realm_access"]
        ):
            scopes += scope_to_list(
                introspected_token["realm_access"]["roles"],
            )
        return scopes
    except Exception as e:
        print("Exception during token introspection:", e)
        return None


def deserialize_schema_from_params(schema_dataclass: type,
                                   key: str = "parameters"):
    """
    Validate and deserialize the incoming request GET args against a
    predefined marshmallow schema.

    This decorator verifies whether an incoming request's schema matches the
    one specified in the given schema, and deserializes it into the specified
    dataclass.

    If an invalid request schema was provided, the request handling will
    immediately terminate by returning an API error and the 400 status code.

    Args:
        schema_dataclass: dataclass representing the request schema, which the
                          request GET params will be deserialized to.
        key: argument name for the deserialized structure.
             The receiving argument must be of the type as specified
             in `schema_dataclass`.
    """

    def _deserialize_schema_from_params(f):
        @functools.wraps(f)
        def __deserialize_schema_from_params(*args, **kwargs):
            if not hasattr(schema_dataclass, "Schema"):
                raise RuntimeError(
                    "get_parameters requires a dataclass decorated "
                    "with the @marshmallow_dataclass.dataclass decorator"
                )
            try:
                parameters: schema_dataclass = schema_dataclass.Schema().load(
                    request.args.to_dict()
                )
            except ValidationError as e:
                return api_error(
                    f"schema validation failed: {e.messages}", 400
                )
            spec = inspect.getfullargspec(f)
            if key in kwargs:
                raise RuntimeError(
                    "deserialize_schema_from_params decorator was used,"
                    "but the wrapped "
                    f"route function <{f.__name__}> is already receiving an "
                    f"argument with the name: <{key}>"
                )
            if key not in spec.args:
                raise KeyError(
                    "deserialize_schema_from_params decorator was used,"
                    "but the wrapped "
                    f"route function <{f.__name__}> does not accept the "
                    f"deserialized structure parameter (missing function "
                    f"argument: <{key}> of type: "
                    f"<{schema_dataclass.__name__}>)"
                )
            kwargs[key] = parameters
            return f(*args, **kwargs)
        return __deserialize_schema_from_params
    return _deserialize_schema_from_params


def deserialize_schema(schema_dataclass: type, key: str = "payload"):
    """
    Validate and deserialize the incoming request against a predefined
    marshmallow schema.

    This decorator verifies whether an incoming request's schema matches the
    one specified in the given schema, and deserializes it into the specified
    dataclass.

    If an invalid request schema was provided, the request handling will
    immediately terminate by returning an API error and the 400 status code.

    Args:
        schema_dataclass: dataclass representing the request schema, which the
                          request will be deserialized to.
        key: argument name for the deserialized structure.
             The receiving argument must be of the type as specified
             in `schema_dataclass`.
    """

    def _deserialize(f):
        @functools.wraps(f)
        def __deserialize(*args, **kwargs):
            if not hasattr(schema_dataclass, "Schema"):
                raise RuntimeError(
                    "deserialize_schema requires a dataclass decorated "
                    "with the @marshmallow_dataclass.dataclass decorator"
                )

            try:
                payload: schema_dataclass = schema_dataclass.Schema().load(
                    request.json
                )
            except ValidationError as e:
                return api_error(
                    f"schema validation failed: {e.messages}", 400
                )

            spec = inspect.getfullargspec(f)
            if key in kwargs:
                raise RuntimeError(
                    "deserialize_schema decorator was used, but the wrapped "
                    f"route function <{f.__name__}> is already receiving an "
                    f"argument with the name: <{key}>"
                )
            if key not in spec.args:
                raise KeyError(
                    "deserialize_schema decorator was used, but the wrapped "
                    f"route function <{f.__name__}> does not accept the "
                    f"deserialized structure parameter (missing function "
                    f"argument: <{key}> of type: "
                    f"<{schema_dataclass.__name__}>)"
                )

            kwargs[key] = payload
            return f(*args, **kwargs)

        return __deserialize

    return _deserialize


def device_api(f):
    """Decorator for device APIs

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
            return api_error(
                "invalid authorization - expected authorization type Bearer",
                401,
            )
        if "token" not in auth:
            return api_error("invalid authorization - missing field: token")

        token = decode_and_verify_token(auth["token"])
        if token is None:
            return api_error("invalid token was provided", 401)

        # Update the last accessed timestamp for this device
        try:
            server.instance._devices_db.update_timestamp(
                token.device_id, datetime.datetime.utcnow()
            )
        except Exception as e:
            print(
                f"Failed to update timestamp for device {token.device_id}, "
                f"exception: {e}",
                flush=True,
            )

        kwargs["device_token"] = token
        return f(*args, **kwargs)

    return _device_api


def __management_api(
        scope_check_callback: Callable[[list[str]], bool],
        append_scopes: bool = False):
    """Decorator for management APIs

    This decorator verifies whether an incoming request contains a valid
    management token. If no token was provided, or an invalid/expired one
    was given, the request handling will immediately terminate by
    returning an API error and 401 Unauthorized status code.
    If a valid token is present, the claims of the token are checked for
    the provided required scopes. If any of the scopes are missing, request
    handling will immediately terminate returning an API error and
    403 Forbidden status code.

    Args:
        scope_check_callback: callback that is called with the list of scopes
                              contained within the token. If the client should
                              not be authorized, the callback is expected to
                              return False. Otherwise, True will allow the
                              request to be processed.
        append_scopes: if True, the scopes of the authenticated user will be
                       passed down to the route handler in the request object
                       along with an information about authentication being
                       disabled. This is useful for routes that require
                       additional information about the authenticated
                       user.
    """

    def _management_api_impl(f):
        @functools.wraps(f)
        def __management_api_impl(*args, **kwargs):
            # First, check if authentication was not explicitly disabled
            conf: configuration.ServerConfig = current_app.config[
                "RDFM_CONFIG"
            ]
            if conf.disable_api_auth:
                return f(*args, **kwargs)

            # Extract token from the Authorization header
            auth = request.authorization
            if auth is None:
                return api_error("no Authorization header was provided", 401)
            if auth.type != "bearer":
                return api_error(
                    "invalid authorization - expected authorization type"
                    "Bearer",
                    401,
                )
            if "token" not in auth:
                return api_error(
                    "invalid authorization - missing field: token", 401
                )
            token: str = auth["token"]

            scopes: Optional[list[str]] = __introspect_and_validate_token(
                conf, token
            )
            if scopes is None:
                return api_error("unauthorized", 401)

            if not scope_check_callback(scopes):
                print(
                    "Rejecting request - authenticated user does not "
                    "have the required scopes to access this resource "
                    f"(user claims: {', '.join(scopes)})",
                    flush=True,
                )
                return api_error(
                    "accessing this resource requires OAuth2 scopes "
                    "which are not provided by the authenticated client",
                    403,
                )

            # Verified the token successfully, the user is authorized
            # Call the original view function
            if append_scopes:
                return f(*args, **kwargs, scopes=scopes)
            else:
                return f(*args, **kwargs)

        return __management_api_impl

    return _management_api_impl


def upgrade_to_websocket(f):
    """Upgrade a request to WebSocket.

    This decorator upgrades an incoming request to a WebSocket.
    The connected socket is passed in as `ws` kwarg to the wrapped
    function.

    On return from the decorated function, the WebSocket connection
    will be closed with the normal disconnection status (1000).
    Additionally, all exceptions of type `WebSocketException` thrown
    by the function will be caught here, which allows customizing
    the WebSocket disconnection status code and message.

    The function that is to be decorated should register it's route
    with the Flask app/blueprint like so:

        @example_blueprint.route('/my/websocket/route', websocket=True)

    The registration decorator must appear before this one. This has
    the added benefit of being able to reject requests at the initial
    handshake, for example:

        @example_blueprint.route('/my/websocket/route', websocket=True)
        @<a decorator that checks for Authorization header>
        @upgrade_to_websocket
        def my_route():
            pass
    """
    __add_scope_docs(f, DOCS_WEBSOCKET_ROUTE)

    @functools.wraps(f)
    def __upgrade(*args, **kwargs):
        spec = inspect.getfullargspec(f)
        if "ws" in kwargs:
            raise RuntimeError(
                "upgrade_to_websocket decorator was used, but the wrapped"
                f"route function <{f.__name__}> is already receiving an "
                "argument with the name 'ws'"
            )
        if "ws" not in spec.args:
            raise KeyError(
                "upgrade_to_websocket decorator was used, but the wrapped "
                f"route function <{f.__name__}> does not accept the WebSocket "
                "client parameter (wissing function argument 'ws' of type "
                "simple_websocket.Client)"
            )

        ws = Server.accept(request.environ, ping_interval=WS_PING_INTERVAL)

        kwargs["ws"] = ws
        try:
            f(*args, **kwargs)
            ws.close()
        except WebSocketException as e:
            try:
                ws.close(reason=e.status_code, message=e.message)
            except ConnectionClosed:
                pass
        except ConnectionClosed:
            pass

        # Depending on the WSGI server used, we need to return a different
        # value to indicate that the request was already handled.
        class WebSocketResponse(Response):
            def __call__(self, *args, **kwargs):
                if ws.mode == "gunicorn":
                    raise StopIteration()
                elif ws.mode == "werkzeug":
                    return super().__call__(*args, **kwargs)
                else:
                    return []

        return WebSocketResponse()

    return __upgrade


def management_read_only_api(f):
    """Decorator to be used on read-only management API routes

    This decorator verifies if the requester has read-only access
    to the protected resource.
    """
    def client_read_allowed(scopes: list[str]) -> bool:
        return SCOPE_READ_WRITE in scopes or SCOPE_READ_ONLY in scopes

    # Mark the handler function with a custom attribute
    f.__rdfm_api_privileges__ = "management_ro"
    __add_scope_docs(f, DOCS_SCOPE_RO_TEXT)

    return __management_api(client_read_allowed)(f)


def management_read_write_api(f):
    """Decorator to be used on read-write management API routes

    This decorator verifies if the requester has read-write access
    to the protected.
    """
    def client_has_rw_scope(scopes):
        return SCOPE_READ_WRITE in scopes

    # Mark the handler function with a custom attribute
    f.__rdfm_api_privileges__ = "management_rw"
    __add_scope_docs(f, DOCS_SCOPE_RW_TEXT)

    return __management_api(client_has_rw_scope)(f)


def artifact_type_to_scope(artifact_type: str) -> str:
    """Convert an artifact type to the corresponding scope that is required
    for this artifact to be uploaded.

    Args:
        artifact_type: artifact type string

    Returns:
        The corresponding scope string
    """
    if artifact_type == "single-file":
        return SCOPE_SINGLE_FILE
    if artifact_type == "rootfs-image":
        return SCOPE_ROOTFS_IMAGE
    return SCOPE_READ_WRITE


def get_scopes_for_upload_package(artifact_type: str) -> bool:
    """Get the scopes required to upload a package of the given type.
    Any of the returned scopes will be sufficient to upload a package.

    Args:
        artifact_type: artifact type string

    Returns:
        A list of scopes, that are required to upload
        a package of the given type
    """
    required_scope = artifact_type_to_scope(artifact_type)
    return list(set([required_scope, SCOPE_READ_WRITE]))


def management_upload_package_api(f):
    """Decorator used to be used on upload_package API route.

    This decorator passes the scopes of the authenticated user
    to the wrapped function.
    """
    def scope_check_callback(scopes):
        return True

    # Mark the handler function with a custom attribute
    f.__rdfm_api_privileges__ = "management_upload_package"
    __add_scope_docs(f, DOCS_SCOPE_PACKAGE_TEXT)

    return __management_api(scope_check_callback, append_scopes=True)(f)


def public_api(f):
    """Decorator to be used on public API routes

    These routes do not require authorization.
    This should be used with caution.
    """
    f.__rdfm_api_privileges__ = "public"
    __add_scope_docs(f, DOCS_PUBLIC_API_TEXT)
    return f
