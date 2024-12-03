import datetime
import traceback
from typing import List, Optional
from flask import Blueprint, request
import models.device
import models.group
from rdfm.schema.v1.logs import LogRouteParameters, LogBatch, Log
from auth.token import DeviceToken
import models.log
import server
from api.v1.common import api_error
from api.v1.middleware import (
    deserialize_schema,
    deserialize_schema_from_params,
    device_api,
    management_read_only_api,
    management_read_write_api
)
from email.utils import parsedate_to_datetime


logs_blueprint: Blueprint = Blueprint("rdfm-server-logs", __name__)


def model_to_schema(log: models.log.Log) -> Log:
    """Convert a log model to the schema model"""
    return Log(
        id=log.id,
        created=log.created,
        device_id=log.device_id,
        device_timestamp=log.device_timestamp,
        name=log.name,
        entry=log.entry
    )


def log_model_generator(
        batch: LogBatch, device_id: int, date: datetime.datetime):
    """
    We are using a generator here as opposed to list comprehension
    to avoid a continuous block when handling large amounts of log entries,
    this generator call should be interweaved in-between IO-bound operations
    to let the server thread handle other requests if necessary.
    """
    for entry in batch.batch:
        log = models.log.Log()
        log.created = date
        log.device_timestamp = entry.device_timestamp
        log.name = entry.name
        log.entry = entry.entry
        log.device_id = device_id
        yield log


@logs_blueprint.route("/api/v1/logs", methods=["POST"])
@device_api
@deserialize_schema(schema_dataclass=LogBatch, key="batch")
def create(device_token: DeviceToken, batch: LogBatch):
    """Create multiple log entries.

    :status 200: no error, log entry was received
    :status 400: log batch missing or malformed
    :status 401: device did not provide authorization data,
                 or the authorization has expired

    **Example Request**

    .. sourcecode:: http

        POST /api/v1/logs
        Content-Type: application/json

        {
            "batch": [
                {
                    "device_timestamp": "Wed, 02 Oct 2002 15:00:00 -0000",
                    "name": "CPU",
                    "entry": "0.123"
                },
                {
                    "device_timestamp": "Wed, 02 Oct 2002 15:00:00 -0000",
                    "name": "MEM",
                    "entry": "0.456"
                }
            ]
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
    """
    try:
        # get the device's primary key
        device = server.instance._devices_db.get_device_data(
            device_token.device_id
        )

        success = server.instance._logs_db.create(
            log_model_generator(
                batch, device.id, datetime.datetime.utcnow()))
        if not success:
            return api_error("could not create log entries", 500)

        return {}, 200

    except Exception as e:
        traceback.print_exc()
        print("Exception during log creation:", repr(e))
        return {}, 500


@logs_blueprint.route("/api/v1/logs/device/<int:identifier>")
@management_read_only_api
@deserialize_schema_from_params(schema_dataclass=LogRouteParameters,
                                key="params")
def fetch_by_device_id(identifier: int, params: LogRouteParameters):
    """Fetch multiple logs by a device identifier, name and date range

    :status 200: no error, log entries were fetched
    :status 400: GET parameters malformed
    :status 401: manager did not provide authorization data,
                 or the authorization has expired
    :status 404: device of the given identifier not found
    """
    try:
        # check if device with the given ID exists
        dev: Optional[
            models.device.Device
        ] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error(
                f"device with an ID of {identifier} does not exist",
                404
            )

        # since fetch supports fetching by multiple IDs and names,
        # encapsulate them in a list if necessary
        logs = server.instance._logs_db.fetch([identifier],
                                              [params.name]
                                              if params.name else None,
                                              params.since, params.to)

        return Log.Schema().dump(
            [model_to_schema(log) for log in logs], many=True
        )
    except Exception as e:
        traceback.print_exc()
        print("Exception during log fetch:", repr(e))
        return api_error("log fetching failed", 500)


@logs_blueprint.route("/api/v1/logs/group/<int:identifier>")
@management_read_only_api
@deserialize_schema_from_params(schema_dataclass=LogRouteParameters,
                                key="params")
def fetch_by_group_id(identifier: int, params: LogRouteParameters):
    """Fetch multiple logs by a group identifier, name and date range

    :status 200: no error, log entries were fetched
    :status 400: GET parameters malformed
    :status 401: manager did not provide authorization data,
                 or the authorization has expired
    :status 404: group of the given identifier not found
    """
    try:
        # check if the group with the given ID exists
        group: Optional[
            models.group.Group
        ] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error(
                f"group with an ID of {identifier} does not exist",
                404
            )

        # get the associated devices
        devices: List[
            models.device.Device
        ] = server.instance._groups_db.fetch_assigned(identifier)
        if not devices:
            return {}, 200

        identifiers = [device.id for device in devices]
        # since fetch supports fetching by multiple IDs and names,
        # encapsulate them in a list if necessary
        logs = server.instance._logs_db.fetch(identifiers,
                                              [params.name]
                                              if params.name else None,
                                              params.since, params.to)

        return Log.Schema().dump(
            [model_to_schema(log) for log in logs], many=True
        )
    except Exception as e:
        traceback.print_exc()
        print("Exception during log fetch:", repr(e))
        return api_error("log fetching failed", 500)


@logs_blueprint.route("/api/v1/logs/<int:identifier>")
@management_read_only_api
def fetch_by_log_id(identifier: int):
    """Fetch a single log by a log identifier

    :status 200: no error, log entry was fetched
    :status 401: manager did not provide authorization data,
                 or the authorization has expired
    :status 404: log with the given identifier not found
    """
    try:
        log: Optional[
            models.log.Log
        ] = server.instance._logs_db.fetch_one(identifier)
        if log is None:
            return api_error("log does not exist", 404)

        return Log.Schema().dump(model_to_schema(log)), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during log fetch:", repr(e))
        return api_error("log fetching failed", 500)


@logs_blueprint.route(
        "/api/v1/logs/device/<int:identifier>",
        methods=["DELETE"]
)
@management_read_write_api
@deserialize_schema_from_params(schema_dataclass=LogRouteParameters,
                                key="params")
def delete_by_device_id(identifier: int, params: LogRouteParameters):
    """Delete multiple logs by a device identifier, name and date range

    :status 200: no error, log entries were deleted
    :status 400: GET parameters malformed
    :status 401: manager did not provide authorization data,
                 or the authorization has expired
    :status 404: device with the given identifier not found
    """
    try:
        dev: Optional[
            models.device.Device
        ] = server.instance._devices_db.fetch_one(identifier)
        if dev is None:
            return api_error(
                f"device with an ID of {identifier} does not exist",
                404
            )

        # since delete supports deletion by multiple
        # IDs and names, encapsulate them in a list if necessary
        success = server.instance._logs_db.delete([identifier],
                                                  [params.name]
                                                  if params.name else None,
                                                  params.since,
                                                  params.to)
        if not success:
            return api_error("log deletion failed", 500)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during log delete:", repr(e))
        return api_error("log deletion failed", 500)


@logs_blueprint.route("/api/v1/logs/<int:identifier>", methods=["DELETE"])
@management_read_write_api
def delete_by_log_id(identifier: int):
    """Delete a single log by a log identifier

    :status 200: no error, log was deleted
    :status 401: manager did not provide authorization data,
                 or the authorization has expired
    :status 404: log with the given identifier not found
    """
    try:
        log = server.instance._logs_db.fetch_one(identifier)
        if log is None:
            return api_error("specified log does not exist", 404)

        if not server.instance._logs_db.delete_one(identifier):
            return api_error("delete failed", 500)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during log delete:", repr(e))
        return api_error("log deletion failed", 500)


@logs_blueprint.route(
        "/api/v1/logs/group/<int:identifier>", methods=["DELETE"]
)
@management_read_write_api
@deserialize_schema_from_params(schema_dataclass=LogRouteParameters,
                                key="params")
def delete_by_group_id(identifier: int, params: LogRouteParameters):
    """Delete multiple logs by a group identifier, name and date range

    :status 200: no error, log entries were deleted
    :status 400: GET parameters malformed
    :status 401: manager did not provide authorization data,
                 or the authorization has expired
    :status 404: group with the given identifier not found
    """
    try:
        group: Optional[
            models.group.Group
        ] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error(
                f"group with an ID of {identifier} does not exist",
                404
            )

        devices: List[
            models.device.Device
        ] = server.instance._groups_db.fetch_assigned(identifier)
        if not devices:
            return {}, 200

        identifiers = [device.id for device in devices]
        # since delete supports deletion by multiple
        # IDs and names, encapsulate them in a list if necessary
        success = server.instance._logs_db.delete(identifiers,
                                                  [params.name]
                                                  if params.name else None,
                                                  params.since, params.to)
        if not success:
            return api_error("log deletion failed", 500)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during log delete:", repr(e))
        return api_error("log deletion failed", 500)
