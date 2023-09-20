import inspect
import functools
from marshmallow import ValidationError
import marshmallow_dataclass
from flask import request
from api.v1.common import api_error


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

