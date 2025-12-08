from dataclasses import field
import marshmallow_dataclass
import marshmallow
from typing import ClassVar, Type


@marshmallow_dataclass.dataclass
class LeaseTopicResponse():
    """Represents a reponse to a topic lease request
    """
    bootstrap_servers: str = field(metadata={"required": True})
    topic: str = field(metadata={"required": True})
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class CheckTopicResponse:
    """Represents a response to a topic check request
    """
    topic: str = field(metadata={"required": True})
    write: bool = field(metadata={"required": True})
    idempotent_write: bool = field(metadata={"required": True})
