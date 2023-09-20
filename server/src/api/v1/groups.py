import datetime
import traceback
from typing import List, Optional
from flask import (
    Flask,
    request,
    Response,
    abort,
    send_from_directory,
    Blueprint
)
import server
from api.v1.common import api_error
import models.group
import models.device
from rdfm.schema.v1.groups import (Group,
                                   AssignDeviceRequest,
                                   AssignPackageRequest)
from api.v1.middleware import deserialize_schema


groups_blueprint: Blueprint = Blueprint("rdfm-server-groups", __name__)


def model_to_schema(group: models.group.Group) -> Group:
    """ Convert a database group model to a schema model.

    As we have to fetch the device list, this can't be done using just a simple
    mapping between the fields.
    """
    return Group(id=group.id,
                 created=group.created,
                 package_id=group.package_id,
                 devices=[ device.id for device in server.instance._groups_db.fetch_assigned(group.id) ],
                 metadata=group.info)


@groups_blueprint.route('/api/v1/groups')
def fetch_all():
    """ Fetch all groups

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr integer id: group identifier
    :>jsonarr string created: creation date
    :>jsonarr optional[integer] package_id: currently assigned package identifier
    :>jsonarr array[integer] devices: currently assigned device identifiers
    :>jsonarr dict[str, str] metadata: group metadata


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/groups HTTP/1.1
        Accept: application/json, text/javascript


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "created": "Mon, 14 Aug 2023 11:00:56 GMT",
                "devices": [],
                "id": 1,
                "package_id": null,
                "metadata": {}
            }
        ]
    """
    try:
        groups: List[models.group.Group] = server.instance._groups_db.fetch_all()
        return Group.Schema().dumps([ model_to_schema(group) for group in groups ], many=True)
    except Exception as e:
        traceback.print_exc()
        print("Exception during group fetch:", repr(e))
        return api_error("fetching failed", 500)


@groups_blueprint.route('/api/v1/groups/<int:identifier>')
def fetch_one(identifier: int):
    """ Fetch information about a group

    :param identifier: group identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: group does not exist

    :>json integer id: group identifier
    :>json string created: creation date
    :>json optional[integer] package_id: currently assigned package identifier
    :>json array[integer] devices: currently assigned device identifiers
    :>json dict[str, str] metadata: group metadata


    **Example Request**

    .. sourcecode:: http

        GET /api/v1/groups/1 HTTP/1.1
        Accept: application/json, text/javascript

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "created": "Mon, 14 Aug 2023 11:00:56 GMT",
            "devices": [],
            "id": 1,
            "package_id": null,
            "metadata": {}
        }
    """
    try:
        group: Optional[models.group.Group] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error("group does not exist", 404)

        return Group.Schema().dumps(model_to_schema(group)), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group fetch:", repr(e))
        return api_error("fetching failed", 500)


@groups_blueprint.route('/api/v1/groups/<int:identifier>', methods=['DELETE'])
def delete_one(identifier: int):
    """ Delete a group

    The group being deleted **must NOT** be assigned to any devices.

    :param identifier: group identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to delete groups
    :status 404: group does not exist
    :status 409: at least one device is still assigned to the group


    **Example Request**

    .. sourcecode:: http

        DELETE /api/v1/groups/1 HTTP/1.1

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        group: Optional[models.group.Group] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error("group does not exist", 404)

        success = server.instance._groups_db.delete(identifier)
        if not success:
            return api_error("group is still assigned to some devices", 409)

        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group delete:", repr(e))
        return api_error("deleting failed", 500)


@groups_blueprint.route('/api/v1/groups/<int:identifier>/devices', methods=['PATCH'])
@deserialize_schema(schema_dataclass=AssignDeviceRequest, key='instructions')
def change_assigned(identifier: int, instructions: AssignDeviceRequest):
    """ Modify the list of devices assigned to a group

    This endpoint allows modifying the list of devices assigned to the group,
    as described by two arrays containing device identifiers of devices that
    will be added/removed from the group.

    This operation is atomic - if at any point an invalid device identifier is
    encountered, the entire operation is aborted. This covers:

        - Any device identifier which does not match a registered device
        - Any device identifier in `additions` which already has an assigned group
          (even if the group is the as specified by `identifier`)
        - Any device identifier in `removals` which is not currently assigned to the
          specified package

    Additions are evaluated first, followed by the removals.

    :param identifier: group identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to delete groups
    :status 404: group does not exist
    :status 409: one of the conflict situations described above has occurred

    :<json array[string] add: identifiers of devices that should be assigned to the group
    :<json array[string] remove: identifiers of devices that should be removed from the group


    **Example request**

    .. sourcecode:: http

        PATCH /api/v1/groups/1/devices HTTP/1.1
        Accept: application/json, text/javascript

        {
            "add": [
                1,
                2,
                5,
            ]
            "remove": [
                3,
            ]
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        group: Optional[models.group.Group] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error("group does not exist", 404)

        err = server.instance._groups_db.modify_assignment(identifier,
                                                           instructions.add,
                                                           instructions.remove)
        if err is not None:
            return api_error(err, 409)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group assignment modification:", repr(e))
        return api_error("group assignment modification failed", 500)


@groups_blueprint.route('/api/v1/groups', methods=['POST'])
def create():
    """ Create a new group

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to create groups
    :status 404: group does not exist

    :<json any key: metadata value

    **Example request**

    .. sourcecode:: http

        POST /api/v1/groups/1 HTTP/1.1
        Content-Type: application/json
        Accept: application/json, text/javascript

        {
            "description": "A test group",
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "created": "Mon, 14 Aug 2023 11:50:40 GMT",
            "devices": [],
            "id": 2,
            "package_id": null,
            "metadata": {
                "description": "A test group",
            }
        }
    """
    try:
        metadata = request.json

        group = models.group.Group()
        group.created = datetime.datetime.utcnow()
        group.info = metadata
        server.instance._groups_db.create(group)

        return Group.Schema().dumps(model_to_schema(group)), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group creation:", repr(e))
        return api_error("group creation failed", 500)


@groups_blueprint.route('/api/v1/groups/<int:identifier>/package', methods=['POST'])
@deserialize_schema(schema_dataclass=AssignPackageRequest, key='package')
def assign_package(identifier: int, package: AssignPackageRequest):
    """ Assign a package to a specific group

    :param identifier: group identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to assign packages
    :status 404: the specified package or group does not exist
    :status 409: the package/group was modified or deleted during the operation

    :<json optional[integer] package_id: identifier of the package to assign, or null


    **Example request**

    .. sourcecode:: http

        POST /api/v1/groups/1/package HTTP/1.1
        Content-Type: application/json
        Accept: application/json, text/javascript

        {
            "package_id": 1,
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        package_id: Optional[int] = package.package_id
        if package_id is not None:
            if server.instance._packages_db.fetch_one(package_id) is None:
                return api_error("package does not exist", 404)

        group: Optional[models.group.Group] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error("group does not exist", 404)

        err = server.instance._groups_db.modify_package(identifier, package_id)
        if err is not None:
            return api_error(err, 409)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group package assignment:", repr(e))
        return api_error("group package assignment failed", 500)
