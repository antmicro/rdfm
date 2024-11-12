import datetime
from dataclasses import field
from typing import ClassVar, Type
import marshmallow
import marshmallow_dataclass


@marshmallow_dataclass.dataclass
class Permission():
    """ Represents permission returned by the API

    Note: when deserializing the response of the "fetch all" endpoint,
    pass `many=True` to the load options.
    """
    id: int = field(metadata={
        "required": False,
        "load_default": None,
    })
    resource: str = field(metadata={
        "required": True,
    })
    created: datetime.datetime = field(metadata={
        "required": False,
        "load_default": None,
        "format": "rfc",
    })
    user_id: str = field(metadata={
        "required": True,
    })
    resource_id: int = field(metadata={
        "required": True
    })
    permission: str = field(metadata={
        "required": True
    })

    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema
