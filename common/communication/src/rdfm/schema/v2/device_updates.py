from marshmallow_dataclass import dataclass
from typing import ClassVar, Type
import marshmallow
from dataclasses import field
from datetime import datetime


@dataclass
class DeviceUpdate():
    """ Represents progress in updating a device """
    id: int = field(metadata={
        "required": True,
    })
    mac_address: str = field(metadata={
        "required": True,
    })
    created: datetime = field(metadata={
        "required": True,
        "format": "rfc",
    })
    version: str = field(metadata={
        "required": True,
    })
    progress: int = field(metadata={
        "required": True,
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema
