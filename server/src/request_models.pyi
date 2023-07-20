from enum import Enum
from pydantic import BaseModel, PositiveInt as PositiveInt, conint as conint
from typing import Union

class Request(BaseModel): ...

class ClientGroups(str, Enum):
    USER: str
    DEVICE: str

class ClientRequest(BaseModel):
    name: str
    group: ClientGroups

class RegisterRequest(Request):
    method: None
    client: ClientRequest

class ListRequest(Request):
    method: None

class InfoDeviceRequest(Request):
    method: None
    device_name: str

class ProxyDeviceRequest(Request):
    method: None
    device_name: str

class ProxyRequest(Request):
    method: None
    port: None

class UpdateDeviceRequest(Request):
    method: None
    device_name: str

class UpdateRequest(Request):
    method: None

class UploadDeviceRequest(Request):
    method: None
    file_path: str
    src_file_path: str
    device_name: str

class UploadRequest(Request):
    method: None
    file_path: str

class DownloadDeviceRequest(Request):
    method: None
    file_path: str
    device_name: str

class DownloadRequest(Request):
    method: None
    file_path: str

class SendFileRequest(Request):
    method: None
    file_path: str
    part: PositiveInt
    parts_total: PositiveInt
    content: str

class FileCompletedRequest(Request):
    method: None
    file_path: str

class Alert(Request):
    method: None
    alert: dict

class Metadata(BaseModel):
    metadata: dict

class Container(BaseModel):
    data: Union[ClientGroups, RegisterRequest, ListRequest, InfoDeviceRequest, ProxyDeviceRequest, ProxyRequest, UpdateDeviceRequest, UpdateRequest, UploadDeviceRequest, UploadRequest, DownloadDeviceRequest, DownloadRequest, SendFileRequest, FileCompletedRequest, Alert, Metadata]
