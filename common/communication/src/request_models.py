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

class DeviceRequest(Request):
    method: str
    device_name: str

class DeviceRequest(Request):
    method: str
    device_name: str

class ClientGroups(str, Enum):
    USER = "USER"
    DEVICE = "DEVICE"

class ClientRequest(BaseModel):
    name: str
    group: ClientGroups
    capabilities: Optional[dict] = None
    mac_address: Optional[str] = None

class RegisterRequest(Request):
    method: Literal['register'] = 'register'  
    client: ClientRequest

class AuthTokenRequest(Request):
    method: Literal['auth_token'] = 'auth_token'
    jwt: str

class ListRequest(Request):
    method: Literal['list'] = 'list'  


class InfoDeviceRequest(DeviceRequest):
    method: Literal['info'] = 'info'  
    device_name: str

class ProxyDeviceRequest(DeviceRequest):
    method: Literal['proxy'] = 'proxy'  
    device_name: str

class ProxyRequest(Request):
    method: Literal['proxy'] = 'proxy'  
    port: conint(ge = 0, le = 65535)

class UpdateDeviceRequest(DeviceRequest):
    method: Literal['update'] = 'update'  
    device_name: str

class UpdateRequest(Request):
    method: Literal['update'] = 'update'  

class UploadDeviceRequest(DeviceRequest):
    method: Literal['upload'] = 'upload'  
    file_path: str
    src_file_path: str
    device_name: str

class UploadRequest(Request):
    method: Literal['upload'] = 'upload'  
    file_path: str

class DownloadDeviceRequest(DeviceRequest):
    method: Literal['download'] = 'download'  
    file_path: str
    dst_file_path: str
    device_name: str

class DownloadRequest(Request):
    method: Literal['download'] = 'download'  
    file_path: str
    url: str

class Alert(Request):
    method: Literal['alert'] = 'alert'  
    alert: dict

class Metadata(BaseModel):
    metadata: dict

class Container(BaseModel):
    """container holds a list of models to enable parsing from json"""
    data: Union[
        ClientGroups,
        RegisterRequest,
        ListRequest,
        InfoDeviceRequest,
        ProxyDeviceRequest,
        ProxyRequest,
        UpdateDeviceRequest,
        UpdateRequest,
        UploadDeviceRequest,
        UploadRequest,
        DownloadDeviceRequest,
        DownloadRequest,
        AuthTokenRequest,
        Alert,
        Metadata
    ]