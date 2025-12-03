import device_mgmt.fs
from flask import Blueprint, current_app, send_from_directory, abort, request, make_response
from typing import Optional, List
import server
import traceback
import models.device
import models.action_log
import json
from api.v1.common import api_error
from api.v1.middleware import (
    check_permission,
    check_device_permission,
    deserialize_schema,
    public_api
)
from rdfm.permissions import (
    READ_PERMISSION,
    UPDATE_PERMISSION,
    CREATE_PERMISSION,
    DEVICE_RESOURCE,
    DELETE_PERMISSION
)
from rdfm.schema.v2.devices import Device, ActionLog, ActionRemoveRequest
from rdfm.schema.v2.fs import FsFile
import device_mgmt.action
import configuration
from pathlib import Path


devices_blueprint: Blueprint = Blueprint("rdfm-server-devices", __name__)


def model_to_schema(device: models.device.Device) -> Device:
    """Convert a database model to the schema model"""
    return Device(
        id=device.id,
        last_access=device.last_access,
        name=device.name,
        mac_address=device.mac_address,
        capabilities=json.loads(device.capabilities),
        metadata=json.loads(device.device_metadata),
        public_key=device.public_key,
        groups=server.instance._devices_db.fetch_groups(device.id),
        connected=True if server.instance.remote_devices.get(device.mac_address) else False
    )


def action_model_to_schema(task: models.action_log.ActionLog) -> Device:
    """Convert a database model to the schema model"""
    return ActionLog(
        action=task.action_id,
        created=task.created,
        status=task.status
    )


@devices_blueprint.route('/api/v2/devices')
@check_permission(DEVICE_RESOURCE, READ_PERMISSION)
def fetch_all():
    """Fetch a list of devices registered on the server

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr integer id: device identifier
    :>jsonarr string last_access: UTC datetime of last access to the server (RFC822)
    :>jsonarr string name: device-reported user friendly name
    :>jsonarr string mac_addr: device-reported MAC address
    :>jsonarr optional[array[integer]] groups: group identifiers of assigned groups
    :>jsonarr dict[str, str] metadata: device metadata (key/value pairs)
    :>jsonarr dict[str, bool] capabilities: device RDFM client capabilities
    :>jsonarr bool connected: device connection status


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/devices HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
          {
            "capabilities": {
              "exec_cmds": false,
              "file_transfer": true,
              "shell_connect": true
            },
            "groups": [1],
            "id": 1,
            "last_access": null,
            "mac_address": "loopback",
            "metadata": {},
            "name": "dummy_device"
          }
        ]
    """  # noqa: E501
    try:
        devices: List[
            models.device.Device
        ] = server.instance._devices_db.fetch_all()
        return Device.Schema().dump(
            [model_to_schema(device) for device in devices], many=True
        ), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during device fetch:", repr(e))
        return api_error("device fetching failed", 500)


@devices_blueprint.route('/api/v2/devices/<int:identifier>')
@check_permission(DEVICE_RESOURCE, READ_PERMISSION)
def fetch_one(identifier: int):
    """ Fetch information about a single device given by the identifier

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: device with the specified identifier does not exist

    :>json integer id: device identifier
    :>json string last_access: UTC datetime of last access to the server (RFC822)
    :>json string name: device-reported user friendly name
    :>json string mac_addr: device-reported MAC address
    :>json optional[array[integer]] groups: group identifiers of assigned groups
    :>json dict[str, str] metadata: device metadata (key/value pairs)
    :>json dict[str, bool] capabilities: device RDFM client capabilities
    :>json bool connected: device connection status


    **Example Request**

    .. sourcecode:: http

        GET /api/v2/devices/1 HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "capabilities": {
            "exec_cmds": false,
            "file_transfer": true,
            "shell_connect": true
          },
          "groups": [1],
          "id": 1,
          "last_access": null,
          "mac_address": "loopback",
          "metadata": {},
          "name": "dummy_device"
        }
    """  # noqa: E501
    try:
        dev: Optional[
            models.device.Device
        ] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error("device does not exist", 404)

        return Device.Schema().dump(model_to_schema(dev)), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during device fetch:", repr(e))
        return api_error("device fetching failed", 500)


@devices_blueprint.route(
    "/api/v2/devices/<string:mac_address>/action/list"
)
@check_device_permission(READ_PERMISSION)
def list_actions(
    mac_address: str
):
    """ Fetch the list of actions executable on the device.

    :status 200: no error

    :>json string action_id: action identifier
    :>json string action_name: human readable name
    :>json array[string] command: command to execute
    :>json string description: human readable description
    :>json number timeout: command timeout

    **Example Request**

    .. sourcecode:: http

        GET /api/v2/devices/d8:5e:d3:86:02:f2/action/list HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
        {
            "action_id": "echo",
            "action_name": "Echo",
            "command": [
            "echo",
            "Executing echo action"
            ],
            "description": "Description of echo action",
            "timeout": 1.0
        },
        {
            "action_id": "sleepTwoSeconds",
            "action_name": "Sleep 2",
            "command": [
            "sleep",
            "2"
            ],
            "description": "Description of sleep 2 seconds action",
            "timeout": 3.0
        },
        {
            "action_id": "sleepFiveSeconds",
            "action_name": "Sleep 5",
            "command": [
            "sleep",
            "5"
            ],
            "description": "This action will timeout",
            "timeout": 3.0
        }
        ]

    """

    return [x.model_dump() for x in device_mgmt.action.ensure_actions(mac_address)], 200


@devices_blueprint.route(
    "/api/v2/devices/<string:mac_address>/action/exec/<string:action_id>"
)
@check_device_permission(UPDATE_PERMISSION)
def exec_action(
    mac_address: str,
    action_id: str
):
    """ Execute action on the device.

    :status 200: no error
    :status 500: action doesn't exist

    :>json string output: base64 encoded action output
    :>json integer status_code: action exit status

    **Example Request**

    .. sourcecode:: http

        GET /api/v2/devices/d8:5e:d3:86:02:f2/action/exec/echo HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "output": "RXhlY3V0aW5nIGVjaG8gYWN0aW9uCg==",
          "status_code": 0
        }
    """
    status_code, output = device_mgmt.action.execute_action(mac_address, action_id)
    return {"status_code": status_code, "output": output}, 200


@devices_blueprint.route(
    "/api/v2/devices/<string:mac_address>/action/log"
)
@check_permission(DEVICE_RESOURCE, READ_PERMISSION)
def get_action_log(mac_address: str):
    """ Fetch a list of actions assigned to the device.

    :status 200: no error

    :>json string action: action name
    :>json string created: date in ISO format
    :>json string status: pending, sent, success or error

    **Example Request**

    .. sourcecode:: http

        GET /api/v2/devices/d8:5e:d3:86:02:f2/action_log HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
        {
            "action": "echo",
            "created": "2025-09-26T12:25:44.638747",
            "status": "pending"
        },
        {
            "action": "sleepTwoSeconds",
            "created": "2025-09-26T12:15:32.047079",
            "status": "success"
        },
        {
            "action": "sleepFiveSeconds",
            "created": "2025-09-26T11:14:55.160802",
            "status": "error"
        },
        ]

    """
    try:
        actions: List[
            models.action_log.ActionLog
        ] = server.instance._action_logs_db.fetch_device_log(mac_address)
        return ActionLog.Schema().dump(
            [action_model_to_schema(action) for action in actions], many=True
        ), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during action log fetch:", repr(e))
        return api_error("action log fetching failed", 500)


@devices_blueprint.route("/api/v2/devices/<string:mac_address>/action/log", methods=['DELETE'])
@check_permission(DEVICE_RESOURCE, UPDATE_PERMISSION)
def clear_action_log(mac_address: str):
    """ Clear device action log.

    This removes all completed actions assigned to the device from the database.

    :status 200: no error


    **Example Request**

    .. sourcecode:: http

        DELETE /api/v2/devices/d8:5e:d3:86:02:f2/action/log HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """
    try:
        server.instance._action_logs_db.delete_device_log(mac_address)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during removal:", repr(e))
        return api_error("removal failed", 500)


@devices_blueprint.route("/api/v2/devices/<string:mac_address>/action/pending", methods=['DELETE'])
@check_permission(DEVICE_RESOURCE, UPDATE_PERMISSION)
def remove_pending_actions(mac_address: str):
    """ Remove pending device actions.

    This removes all pending actions assigned to the device from the database and from the queue.

    :status 200: no error


    **Example Request**

    .. sourcecode:: http

        DELETE /api/v2/devices/d8:5e:d3:86:02:f2/action/pending HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """
    try:
        server.instance._action_logs_db.delete_pending_actions(mac_address)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during removal:", repr(e))
        return api_error("removal failed", 500)


@devices_blueprint.route("/api/v2/devices/<string:mac_address>/action/remove", methods=['POST'])
@check_permission(DEVICE_RESOURCE, UPDATE_PERMISSION)
@deserialize_schema(schema_dataclass=ActionRemoveRequest, key="actions")
def remove_selected_actions(mac_address: str, actions: List[ActionLog]):
    """ Remove selected device actions.

    This removes all selected actions assigned to the device from the database
    regardless of their completion status.

    :status 200: no error


    **Example Request**

    .. sourcecode:: http

        POST /api/v2/devices/d8:5e:d3:86:02:f2/action/remove HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """
    try:
        server.instance._action_logs_db.delete_selected_actions(mac_address, actions.actions)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during removal:", repr(e))
        return api_error("removal failed", 500)


@devices_blueprint.route("/api/v2/devices/<int:identifier>", methods=['DELETE'])
@check_permission(DEVICE_RESOURCE, DELETE_PERMISSION)
def remove(identifier: int):
    """ Delete the device

    This endpoint allows deleting the device.
    As a result, the device will no longer be able to access the server
    without making a new registartion.

    :param identifier: device identifier
    :status 200: no error
    :status 404: the specified device does not exist


    **Example Request**

    .. sourcecode:: http

        DELETE /api/v2/devices/1 HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """
    try:
        dev: Optional[models.device.Device] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error("device does not exist", 404)

        server.instance._devices_db.delete(identifier)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during removal:", repr(e))
        return api_error("removal failed", 500)


@devices_blueprint.route("/api/v2/devices/<int:identifier>/fs/file", methods=['POST'])
@check_permission(DEVICE_RESOURCE, READ_PERMISSION)
@deserialize_schema(schema_dataclass=FsFile, key="fs_file")
def download_file(identifier: int, fs_file: FsFile):
    """ Download file from the device

    This endpoint allows downloading files from the device.

    :status 200: no error
    :status 404: device does not exist
    :status 500: failure during download

    :>json string file: name of file to download

    **Example Request**

    .. sourcecode:: http

        GET /api/v2/devices/1/fs/file HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "status": 0,
          "url": "download.url"
        }
    """
    try:
        dev: Optional[models.device.Device] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error("device does not exist", 404)

        status, download_url = device_mgmt.fs.prepare_download(dev.mac_address, fs_file.file)
        return {"status": status, "url": download_url}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during downloading:", repr(e))
        return api_error("download failed", 500)


@devices_blueprint.route("/local_storage_multipart/multipart/<path:key>", methods=["GET"])
@public_api
def fetch_local_file(key: str):
    """Endpoint for exposing local filesystem storage for multipart download.

    :param key: identifier of the multipart file object in local storage
    :status 200: no error
    :status 404: specified file does not exist
    """
    conf: configuration.ServerConfig = current_app.config["RDFM_CONFIG"]
    storage_location = Path(conf.package_dir).resolve()
    package = (storage_location / "multipart" / key).resolve()
    if not package.is_relative_to(storage_location):
        abort(404)
    return send_from_directory(str(package.parent), str(package.name))


@devices_blueprint.route("/local_storage_multipart/parts/<part>", methods=["PUT"])
@public_api
def upload_local_file_part(part: str):
    """Endpoint for uploading parts of multipart upload to the local filesystem storage.

    :param part: identifier of the multipart file object in local storage
    :status 200: no error
    :status 404: wrong upload part name
    :status 500: failure during upload
    """
    conf: configuration.ServerConfig = current_app.config["RDFM_CONFIG"]
    storage_location = Path(conf.package_dir).resolve()
    package = (storage_location / "multipart" / "parts" / part).resolve()
    if not package.is_relative_to(storage_location):
        abort(404)
    package.parent.mkdir(exist_ok=True, parents=True)
    with open(package, "wb") as part_file:
        part_file.write(request.data)
    resp = make_response()
    resp.status = 200
    resp.headers.set("Etag", part)
    return resp


@devices_blueprint.route("/api/v2/devices/<int:identifier>/tag/<string:tag>", methods=["POST"])
@check_permission(DEVICE_RESOURCE, UPDATE_PERMISSION)
def assign_tag(identifier: int, tag: str):
    """Assign a new tag to a device.

    :param identifier: device identifier
    :param tag: device tag
    :status 200: no error


    **Example request**

    .. sourcecode:: http

        POST /api/v2/devices/1/tag/linux-client HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """
    try:
        server.instance._devices_db.add_tag(identifier, tag)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during tag assignment:", repr(e))
        return api_error("assigning tags failed", 500)


@devices_blueprint.route(
    "/api/v2/devices/<int:identifier>/tags"
)
@check_permission(DEVICE_RESOURCE, READ_PERMISSION)
def fetch_tags(identifier: int):
    """ Fetch a list of tags assigned to the device.

    :param identifier: device identifier
    :status 200: no error

    :>json string tag: device tag


    **Example Request**

    .. sourcecode:: http

        GET /api/v2/devices/1/tags HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            "linux-client",
            "test-device"
        ]

    """
    return server.instance._devices_db.fetch_tags(identifier), 200


@devices_blueprint.route('/api/v2/tags/<string:tag>')
@check_permission(DEVICE_RESOURCE, READ_PERMISSION)
def fetch_by_tag(tag: str):
    """Fetch a list of devices registered on the server with the given tag assigned.

    :param tag: device tag 
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr integer id: device identifier
    :>jsonarr string last_access: UTC datetime of last access to the server (RFC822)
    :>jsonarr string name: device-reported user friendly name
    :>jsonarr string mac_addr: device-reported MAC address
    :>jsonarr optional[array[integer]] groups: group identifiers of assigned groups
    :>jsonarr dict[str, str] metadata: device metadata (key/value pairs)
    :>jsonarr dict[str, bool] capabilities: device RDFM client capabilities
    :>jsonarr bool connected: device connection status


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/tag/linux-client HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
          {
            "capabilities": {
              "exec_cmds": false,
              "file_transfer": true,
              "shell_connect": true
            },
            "groups": [1],
            "id": 1,
            "last_access": null,
            "mac_address": "loopback",
            "metadata": {},
            "name": "dummy_device"
          }
        ]
    """  # noqa: E501
    try:
        devices: List[
            models.device.Device
        ] = server.instance._devices_db.fetch_by_tag(tag)
        return Device.Schema().dump(
            [model_to_schema(device) for device in devices], many=True
        ), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during device fetch:", repr(e))
        return api_error("device fetching failed", 500)
