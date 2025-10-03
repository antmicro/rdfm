from flask import Blueprint
from typing import Optional, List
import server
import traceback
import models.device
import json
from api.v1.common import api_error
from api.v1.middleware import (
    check_permission,
    check_device_permission,
)
from rdfm.permissions import (
    READ_PERMISSION,
    UPDATE_PERMISSION,
    DEVICE_RESOURCE,
    DELETE_PERMISSION
)
from rdfm.schema.v2.devices import Device
import device_mgmt.action

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
        groups=server.instance._devices_db.fetch_groups(device.id)
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

        DELETE /api/v1/devices/1 HTTP/1.1
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
