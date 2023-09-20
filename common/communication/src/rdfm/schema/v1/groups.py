import datetime
from dataclasses import field
from typing import Any, ClassVar, Optional, Type
import marshmallow
import marshmallow_dataclass
from marshmallow import fields


@marshmallow_dataclass.dataclass
class Group():
    """ Represents group data returned by the API

    Note: when deserializing the response of the "fetch all" endpoint,
    pass `many=True` to the load options.
    """
    id: int = field(metadata={
        "required": True,
    })
    created: datetime.datetime = field(metadata={
        "required": True,
        "format": "rfc",
    })
    devices: list[int] = field(metadata={
        "required": True,
    })
    package_id: Optional[int] = field(metadata={
        "required": True,
        "allow_none": True
    })
    metadata: dict[str, Any] = field(metadata={
        "required": True,
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class AssignDeviceRequest():
    """ Represents a group device assignment request
    """
    add: list[int] = field(metadata={
        "required": True,
    })
    remove: list[int] = field(metadata={
        "required": True,
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class AssignPackageRequest():
    """ Represents a group package assignment request
    """
    package_id: int = field(metadata={
        "required": True
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema