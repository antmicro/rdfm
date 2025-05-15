from dataclasses import field
from typing import ClassVar, Type
import marshmallow
import marshmallow_dataclass
from marshmallow import fields
from rdfm.schema.validators import Contains


""" Metadata key for the currently running software version """
META_SOFT_VER = "rdfm.software.version"

""" Metadata key for the device type a package is compatible with """
META_DEVICE_TYPE = "rdfm.hardware.devtype"

""" Metadata key for the device's MAC address """
META_MAC_ADDRESS = "rdfm.hardware.macaddr"

""" Metadata key for the device xdelta support """
META_XDELTA_SUPPORT = "rdfm.software.supports_xdelta"

""" Metadata key for the device rsync support """
META_RSYNC_SUPPORT = "rdfm.software.supports_rsync"


@marshmallow_dataclass.dataclass
class UpdateCheckRequest():
    """ Represents a request from a device to perform an update check
    """
    metadata: dict[str, str] = field(metadata={
        "validate": Contains(choices=[
            META_SOFT_VER,
            META_DEVICE_TYPE,
            META_MAC_ADDRESS
        ])
    })
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema
