# type: ignore

from enum import Enum
from typing import (
    Literal,
    Union,
    Optional
)
from pydantic import (
    BaseModel,
    PositiveInt,
    conint
) 

class Request(BaseModel):
    method: str


class Alert(Request):
    method: Literal['alert'] = 'alert'  
    alert: dict


class CapabilityReport(Request):
    method: Literal['capability_report'] = 'capability_report'
    capabilities: dict[str, bool]

class DeviceAttachToManager(Request):
    method: Literal['shell_attach'] = 'shell_attach'
    mac_addr: str
    uuid: str

class Container(BaseModel):
    """container holds a list of models to enable parsing from json"""
    data: Union[
        Alert,
        CapabilityReport,
        DeviceAttachToManager
    ]
