from enum import Enum
from pydantic import BaseModel, PositiveInt as PositiveInt, conint as conint
from typing import Literal, Optional, Union

class Request(BaseModel):
    method: str

class DeviceRequest(Request):
    method: str
    device_name: str

class DeviceRequest(Request):
    method: str
    device_name: str

class ClientGroups(str, Enum):
    USER: str
    DEVICE: str

class ClientRequest(BaseModel):
    name: str
    group: ClientGroups
    capabilities: Optional[dict]
    mac_address: Optional[str]

class RegisterRequest(Request):
    method: Literal['register']
    client: ClientRequest

class AuthTokenRequest(Request):
    method: Literal['auth_token']
    jwt: str

class ListRequest(Request):
    method: Literal['list']

class InfoDeviceRequest(DeviceRequest):
    method: Literal['info']
    device_name: str

class ProxyDeviceRequest(DeviceRequest):
    method: Literal['proxy']
    device_name: str

class ProxyRequest(Request):
    method: Literal['proxy']
    port: None

class UpdateDeviceRequest(DeviceRequest):
    method: Literal['update']
    device_name: str

class UpdateRequest(Request):
    method: Literal['update']

class UploadDeviceRequest(DeviceRequest):
    method: Literal['upload']
    file_path: str
    src_file_path: str
    device_name: str

class UploadRequest(Request):
    method: Literal['upload']
    file_path: str

class DownloadDeviceRequest(DeviceRequest):
    method: Literal['download']
    file_path: str
    dst_file_path: str
    device_name: str

class DownloadRequest(Request):
    method: Literal['download']
    file_path: str
    url: str

class Alert(Request):
    method: Literal['alert']
    alert: dict

class Metadata(BaseModel):
    metadata: dict

class Container(BaseModel):
    data: Union[ClientGroups, RegisterRequest, ListRequest, InfoDeviceRequest, ProxyDeviceRequest, ProxyRequest, UpdateDeviceRequest, UpdateRequest, UploadDeviceRequest, UploadRequest, DownloadDeviceRequest, DownloadRequest, AuthTokenRequest, Alert, Metadata]
