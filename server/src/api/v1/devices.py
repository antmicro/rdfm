from flask import Blueprint
from typing import Optional, List
import server
import traceback
import models.device
import json
from api.v1.common import api_error
from api.v1.middleware import management_read_only_api, management_read_write_api
from rdfm.schema.v1.devices import Device


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
        group=server.instance._devices_db.fetch_active_group(device.id)
    )


@devices_blueprint.route("/api/v1/devices")
@management_read_only_api
def fetch_all():
    """Fetch a list of devices registered on the server

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr integer id: device identifier
    :>jsonarr string last_access: UTC datetime of last access to the server (RFC822)
    :>jsonarr string name: device-reported user friendly name
    :>jsonarr string mac_addr: device-reported MAC address
    :>jsonarr optional[integer] group: group identifier of assigned group
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
            "group": 1,
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


@devices_blueprint.route("/api/v1/devices/<int:identifier>")
@management_read_only_api
def fetch_one(identifier: int):
    """Fetch information about a single device given by the identifier

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: device with the specified identifier does not exist

    :>json integer id: device identifier
    :>json string last_access: UTC datetime of last access to the server (RFC822)
    :>json string name: device-reported user friendly name
    :>json string mac_addr: device-reported MAC address
    :>json optional[integer] group: group identifier of assigned group
    :>json dict[str, str] metadata: device metadata (key/value pairs)
    :>json dict[str, bool] capabilities: device RDFM client capabilities


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/devices/1 HTTP/1.1
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
          "group": 1,
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


@devices_blueprint.route("/api/v1/devices/<int:identifier>", methods=['DELETE'])
@management_read_write_api
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
