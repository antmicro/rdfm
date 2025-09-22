# type: ignore

from enum import Enum
from typing import (
    Literal,
    Union,
    Optional,
    List,
)
from pydantic import (
    BaseModel,
    PositiveInt,
    conint
)


class Action(BaseModel):
    action_id: str
    action_name: str
    description: str
    command: list[str]
    timeout: float


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


class ActionExec(Request):
    method: Literal['action_exec'] = 'action_exec'
    execution_id: str
    action_id: str


class ActionExecResult(Request):
    method: Literal['action_exec_result'] = 'action_exec_result'
    execution_id: str
    status_code: int
    output: str


class ActionExecControl(Request):
    method: Literal['action_exec_control'] = 'action_exec_control'
    execution_id: str
    status: str


class ActionListQuery(Request):
    method: Literal['action_list_query'] = 'action_list_query'


class ActionListUpdate(Request):
    method: Literal['action_list_update'] = 'action_list_update'
    actions: list[Action]


class FsFileDownload(Request):
    method: Literal['fs_file_download'] = 'fs_file_download'
    id: str
    file: str
    upload_urls: List[str]
    part_size: int


class FsFileDownloadReply(Request):
    method: Literal['fs_file_download_reply'] = 'fs_file_download_reply'
    id: str
    status: int
    etags: List[str]


class FsFileProbe(Request):
    method: Literal['fs_file_probe'] = 'fs_file_probe'
    id: str
    file: str


class FsFileProbeReply(Request):
    method: Literal['fs_file_probe_reply'] = 'fs_file_probe_reply'
    id: str
    status: int
    size: int


class Container(BaseModel):
    """container holds a list of models to enable parsing from json"""
    data: Union[
        Alert,
        CapabilityReport,
        DeviceAttachToManager,
        ActionExecResult,
        ActionListUpdate,
        ActionExecControl,
        Action,
        FsFileDownload,
        FsFileDownloadReply,
        FsFileProbe,
        FsFileProbeReply,
    ]
