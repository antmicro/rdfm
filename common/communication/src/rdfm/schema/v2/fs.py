import datetime
from dataclasses import field
from typing import ClassVar, Type
import marshmallow
import marshmallow_dataclass


@marshmallow_dataclass.dataclass
class FsFile():
    file: str = field(metadata={
        "required": True,
    })

    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema
