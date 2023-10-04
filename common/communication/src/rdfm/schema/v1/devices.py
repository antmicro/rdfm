import datetime
from dataclasses import field
from typing import Any, ClassVar, Optional, Type
import marshmallow
import marshmallow_dataclass
from marshmallow import fields
from rdfm.schema.v1.updates import META_SOFT_VER, META_DEVICE_TYPE, META_MAC_ADDRESS
from rdfm.schema.validators import Contains


@marshmallow_dataclass.dataclass
class AuthRegisterRequest():
    """ Represents a device registration request
    """
    metadata: dict[str, str] = field(metadata={
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
