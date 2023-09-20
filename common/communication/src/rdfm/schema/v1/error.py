from dataclasses import field
from typing import ClassVar, Type
import marshmallow
import marshmallow_dataclass


@marshmallow_dataclass.dataclass
class ApiError:
    """ Represents an error response returned by the server
    """
    error: str = field(metadata={
        "required": True,
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema