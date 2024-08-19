from typing import ClassVar, Type, List
import datetime
from dataclasses import field
from typing import Optional

import marshmallow
from marshmallow import ValidationError
import marshmallow_dataclass
from rdfm.schema.validators import Contains


@marshmallow_dataclass.dataclass
class LogRouteParameters():
    """Represents GET parameters passed to a log route"""
    since: Optional[datetime.datetime] = field(metadata={
        "required": False,
        "format": "rfc"
    })
    to: Optional[datetime.datetime] = field(metadata={
        "required": False,
        "format": "rfc"
    })
    name: Optional[str] = field(metadata={
        "required": False
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class LogEntry():
    """Represents a single log entry within a batch of logs
    """
    device_timestamp: datetime.datetime = field(metadata={
        "required": True,
        "format": "rfc"
    })
    name: str = field(metadata={
        "required": True
    })
    entry: str = field(metadata={
        "required": True
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class LogBatch():
    """Represents a log batch
    """
    batch: List[LogEntry] = field(metadata={
        "required": True
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@marshmallow_dataclass.dataclass
class Log():
    """Represents a log entry
    """
    id: int = field(metadata={
        "required": True
    })
    created: Optional[datetime.datetime] = field(metadata={
        "required": True,
        "allowed_none": True,
        "format": "rfc"
    })
    device_id: int = field(metadata={
        "required": True
    })
    device_timestamp: datetime.datetime = field(metadata={
        "required": True,
        "format": "rfc"
    })
    name: str = field(metadata={
        "required": True
    })
    entry: str = field(metadata={
        "required": True
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema
