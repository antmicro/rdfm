import datetime
from dataclasses import field
from typing import Any, ClassVar, Type
import marshmallow
import marshmallow_dataclass
from marshmallow import fields


@marshmallow_dataclass.dataclass
class Package():
    """ Represents group data returned by the API

    Note: when deserializing the response of the "fetch all" endpoint,
    pass `many=True` to the load options.
    """
    id: int = field(metadata={
        "required": True
    })
    created: datetime.datetime = field(metadata={
        "required": True,
        "format": "rfc"
    })
    sha256: str = field(metadata={
        "required": True
    })
    driver: str = field(metadata={
        "required": True
    })
    # FIXME: The dictionary should map to strings, not any type.
    #        Allowing any type here is a workaround for the server
    #        returning non-string values for metadata.
    metadata: dict[str, Any] = field(metadata={
        "required": True,
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema