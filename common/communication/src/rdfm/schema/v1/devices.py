import datetime
from dataclasses import field
from typing import Any, ClassVar, Optional, Type
import marshmallow
import marshmallow_dataclass
from marshmallow import fields
from rdfm.schema.v1.updates import META_SOFT_VER, META_DEVICE_TYPE, META_MAC_ADDRESS
from rdfm.schema.validators import Contains


@marshmallow_dataclass.dataclass
class Device():
    """ Represents the data of a device
    """
    id: int = field(metadata={
        "required": True
    })
    name: str = field(metadata={
        "required": True
    })
    mac_address: str = field(metadata={
        "required": True
    })
    capabilities: dict[str, bool] = field(metadata={
        "required": True
    })
    metadata: dict[str, str | list] = field(metadata={
        "required": True
    })
    group: Optional[int] = field(metadata={
        "required": True,
        "allow_none": True
    })
    last_access: Optional[datetime.datetime] = field(metadata={
        "required": True,
        "allow_none": True,
        "format": "rfc",
    })
    public_key: str = field(metadata={
        "required": True,
        "allow_none": True
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class Registration():
    """ Represents a registration request
    """
    mac_address: str = field(metadata={
        "required": True
    })
    public_key: str = field(metadata={
        "required": True
    })
    metadata: dict[str, str | list] = field(metadata={
        "required": True
    })
    last_appeared: datetime.datetime = field(metadata={
        "required": True,
        "format": "rfc",
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class AuthRegisterRequest():
    """ Represents a device registration request
    """
    metadata: dict[str, str | list] = field(metadata={
        "required": True,
        "validate": Contains(choices=[
            META_SOFT_VER,
            META_DEVICE_TYPE,
            META_MAC_ADDRESS
        ])
    })
    public_key: str = field(metadata={
        "required": True,
    })
    timestamp: int = field(metadata={
        "required": True,
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class RemovePendingRequest():
    """ Represents a pending device removal request
    """
    public_key: str = field(metadata={
        "required": True,
    })
    mac_address: str = field(metadata={
        "required": True,
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema
