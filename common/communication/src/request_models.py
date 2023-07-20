# type: ignore

from enum import Enum
from typing import Literal, Union
from pydantic import (
    BaseModel,
    PositiveInt,
    conint
) 

class Request(BaseModel):
    pass

class ClientGroups(str, Enum):
    USER = "USER"
    DEVICE = "DEVICE"

class ClientRequest(BaseModel):
    name: str
    group: ClientGroups

class RegisterRequest(Request):
    method: Literal['register'] = 'register'  
    client: ClientRequest


class ListRequest(Request):
    method: Literal['list'] = 'list'  


class InfoDeviceRequest(Request):
    method: Literal['info'] = 'info'  
    device_name: str

class ProxyDeviceRequest(Request):
    method: Literal['proxy'] = 'proxy'  
    device_name: str

class ProxyRequest(Request):
    method: Literal['proxy'] = 'proxy'  
    port: conint(ge = 0, le = 65535)

class UpdateDeviceRequest(Request):
    method: Literal['update'] = 'update'  
    device_name: str

class UpdateRequest(Request):
    method: Literal['update'] = 'update'  

class UploadDeviceRequest(Request):
    method: Literal['upload'] = 'upload'  
    file_path: str
    src_file_path: str
    device_name: str

class UploadRequest(Request):
    method: Literal['upload'] = 'upload'  
    file_path: str

class DownloadDeviceRequest(Request):
    method: Literal['download'] = 'download'  
    file_path: str
    device_name: str

class DownloadRequest(Request):
    method: Literal['download'] = 'download'  
    file_path: str

class SendFileRequest(Request):
    method: Literal['send_file'] = 'send_file'  
    file_path: str
    part: PositiveInt
    parts_total: PositiveInt
    content: str

class FileCompletedRequest(Request):
    method: Literal['file_completed'] = 'file_completed'  
    file_path: str

class Alert(Request):
    method: Literal['alert'] = 'alert'  
    alert: dict

class Metadata(BaseModel):
    metadata: dict

class Container(BaseModel):
    """ container holds a subclass of Request"""
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
        SendFileRequest,
        FileCompletedRequest,
        Alert,
        Metadata
    ]