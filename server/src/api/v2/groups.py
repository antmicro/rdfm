import datetime
import traceback
from typing import List, Optional
from api.v1.middleware import (
    management_read_write_api,
    check_permission,
    add_permissions_for_new_resource,
)
from rdfm.permissions import (
    READ_PERMISSION,
    UPDATE_PERMISSION,
    DELETE_PERMISSION,
    GROUP_RESOURCE,
)
from flask import request, Blueprint
import server
from api.v1.common import api_error
import models.group
import models.device
from rdfm.schema.v2.groups import (
    Group,
    AssignDeviceRequest,
    AssignPackageRequest,
    AssignPolicyRequest,
    AssignPriorityRequest,
)
from api.v1.middleware import deserialize_schema
import update.policy

groups_blueprint: Blueprint = Blueprint("rdfm-server-groups", __name__)

GROUP_DEFAULT_PRIORITY = 25


def model_to_schema(group: models.group.Group) -> Group:
    """Convert a database group model to a schema model.

    As we have to fetch the device list, this can't be done using just a simple
    mapping between the fields.
    """
    return Group(
        id=group.id,
        created=group.created,
        packages=server.instance._groups_db.fetch_assigned_packages(group.id),
        devices=[
            device.id
            for device in server.instance._groups_db.fetch_assigned(group.id)
        ],
        metadata=group.info,
        policy=group.policy,
        priority=group.priority,
    )


@groups_blueprint.route("/api/v2/groups")
@check_permission(GROUP_RESOURCE, READ_PERMISSION)
def fetch_all():
    """Fetch all groups

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired

    :>jsonarr integer id: group identifier
    :>jsonarr string created: UTC creation date (RFC822)
    :>jsonarr array[integer] packages: currently assigned package identifiers
    :>jsonarr array[integer] devices: currently assigned device identifiers
    :>jsonarr dict[str, str] metadata: group metadata
    :>jsonarr str policy: group update policy
    :>jsonarr integer priority: group priority


    **Example Request**

    .. sourcecode:: http

        GET /api/v2/groups HTTP/1.1
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
                "packages": [],
                "metadata": {},
                "policy": "no_update,",
                "priority": 25
            }
        ]
    """
    try:
        groups: List[
            models.group.Group
        ] = server.instance._groups_db.fetch_all()
        return Group.Schema().dump(
            [model_to_schema(group) for group in groups], many=True), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group fetch:", repr(e))
        return api_error("fetching failed", 500)


@groups_blueprint.route("/api/v2/groups/<int:identifier>")
@check_permission(GROUP_RESOURCE, READ_PERMISSION)
def fetch_one(identifier: int):
    """Fetch information about a group

    :param identifier: group identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 404: group does not exist

    :>json integer id: group identifier
    :>json string created: UTC creation date (RFC822)
    :>json array[integer] packages: currently assigned package identifiers
    :>json array[integer] devices: currently assigned device identifiers
    :>json dict[str, str] metadata: group metadata
    :>json str policy: group update policy
    :>json integer priority: group priority


    **Example Request**

    .. sourcecode:: http

        GET /api/v2/groups/1 HTTP/1.1
        Accept: application/json, text/javascript

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "created": "Mon, 14 Aug 2023 11:00:56 GMT",
            "devices": [],
            "id": 1,
            "packages": [],
            "metadata": {},
            "policy": "no_update,",
            "priority": 25
        }
    """
    try:
        group: Optional[
            models.group.Group
        ] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error("group does not exist", 404)

        return Group.Schema().dump(model_to_schema(group)), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group fetch:", repr(e))
        return api_error("fetching failed", 500)


@groups_blueprint.route("/api/v2/groups/<int:identifier>", methods=["DELETE"])
@check_permission(GROUP_RESOURCE, DELETE_PERMISSION)
def delete_one(identifier: int):
    """Delete a group

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

        DELETE /api/v2/groups/1 HTTP/1.1

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        group: Optional[
            models.group.Group
        ] = server.instance._groups_db.fetch_one(identifier)
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


@groups_blueprint.route(
    "/api/v2/groups/<int:identifier>/devices", methods=["PATCH"]
)
@check_permission(GROUP_RESOURCE, UPDATE_PERMISSION)
@deserialize_schema(schema_dataclass=AssignDeviceRequest, key="instructions")
def change_assigned(identifier: int, instructions: AssignDeviceRequest):
    """Modify the list of devices assigned to a group

    This endpoint allows modifying the list of devices assigned to the group,
    as described by two arrays containing device identifiers of devices that
    will be added/removed from the group.

    This operation is atomic - if at any point an invalid device identifier is
    encountered, the entire operation is aborted. This covers:

        - Any device identifier which does not match a registered device
        - Any device identifier in `additions` which already has an assigned
          group which has the same priority as the group specified by
          `identifier`
          (even if the group is the same as specified by `identifier`)
        - Any device identifier in `removals` which is not currently assigned
          to the specified group

    Additions are evaluated first, followed by the removals.

    :param identifier: group identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to delete groups
    :status 404: group does not exist
    :status 409: one of the conflict situations described above has occurred

    :<json array[string] add: identifiers of devices that should be assigned
                              to the group
    :<json array[string] remove: identifiers of devices that should be removed
                                 from the group


    **Example request**

    .. sourcecode:: http

        PATCH /api/v2/groups/1/devices HTTP/1.1
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
        group: Optional[
            models.group.Group
        ] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error("group does not exist", 404)

        err = server.instance._groups_db.modify_assignment(
            identifier, instructions.add, instructions.remove
        )
        if err is not None:
            return api_error(err, 409)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group assignment modification:", repr(e))
        return api_error("group assignment modification failed", 500)


@groups_blueprint.route("/api/v2/groups", methods=["POST"])
@management_read_write_api
@add_permissions_for_new_resource(GROUP_RESOURCE)
def create():
    """Create a new group

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to create groups
    :status 404: group does not exist

    :<json dict[str, str] metadata: device metadata
    :<json optional[int] priority: priority of the group, lower value takes
                                   precedence

    **Example request**

    .. sourcecode:: http

        POST /api/v2/groups/1 HTTP/1.1
        Content-Type: application/json
        Accept: application/json, text/javascript

        {
            priority: 1,
            "metadata":
            {
                "description": "A test group",
            }
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "created": "Mon, 14 Aug 2023 11:50:40 GMT",
            "devices": [],
            "id": 2,
            "packages": [],
            "priority": 1,
            "metadata": {
                "description": "A test group",
            },
            "policy": "no_update,"
        }
    """
    try:
        metadata = request.json["metadata"]

        group = models.group.Group()
        group.created = datetime.datetime.utcnow()
        group.info = metadata
        group.policy = "no_update,"
        if "priority" in request.json:
            group.priority = request.json["priority"]
        else:
            group.priority = GROUP_DEFAULT_PRIORITY
        err = server.instance._groups_db.create(group)
        if err is not None:
            return api_error(err, 409)

        return Group.Schema().dump(model_to_schema(group)), 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group creation:", repr(e))
        return api_error("group creation failed", 500)


@groups_blueprint.route(
    "/api/v2/groups/<int:identifier>/package", methods=["POST"]
)
@check_permission(GROUP_RESOURCE, UPDATE_PERMISSION)
@deserialize_schema(schema_dataclass=AssignPackageRequest, key="assignment")
def assign_package(identifier: int, assignment: AssignPackageRequest):
    """Assign a package to a specific group

    :param identifier: group identifier
    :status 200: no error
    :status 400: invalid request schema
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to assign packages
    :status 404: the specified package or group does not exist
    :status 409: the package/group was modified or deleted during the operation

    :<json array[integer] packages: identifiers of the packages to assign, or
                                    empty array


    **Example request**

    .. sourcecode:: http

        POST /api/v2/groups/1/package HTTP/1.1
        Content-Type: application/json
        Accept: application/json, text/javascript

        {
            "packages": [1],
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        group: Optional[
            models.group.Group
        ] = server.instance._groups_db.fetch_one(identifier)
        if group is None:
            return api_error("group does not exist", 404)

        err = server.instance._groups_db.modify_package(
            identifier, assignment.packages
        )
        if err is not None:
            return api_error(err, 409)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group package assignment:", repr(e))
        return api_error("group package assignment failed", 500)


@groups_blueprint.route(
    "/api/v2/groups/<int:identifier>/policy", methods=["POST"]
)
@check_permission(GROUP_RESOURCE, UPDATE_PERMISSION)
@deserialize_schema(schema_dataclass=AssignPolicyRequest, key="policy_request")
def update_policy(identifier: int, policy_request: AssignPolicyRequest):
    """Change the update policy of the group

    The update policy defines the target versions that each device within
    the group should be receiving.
    For information about group policies, consult the OTA manual.

    :param identifier: group identifier
    :status 200: no error
    :status 400: invalid request schema, or an invalid policy schema
                 was requested
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to modify groups
    :status 404: the specified group does not exist

    :<json string policy: new group policy string to set

    **Example Request**

    .. sourcecode:: http

        POST /api/v2/groups/1/policy HTTP/1.1
        Content-Type: application/json
        Accept: application/json, text/javascript

        {
            "policy": "exact_match,v1",
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        if server.instance._groups_db.fetch_one(identifier) is None:
            return api_error("group does not exist", 404)

        policy: str = policy_request.policy
        try:
            update.policy.create(policy)
        except RuntimeError as e:
            return api_error(f"invalid policy: {e}", 400)

        server.instance._groups_db.update_policy(identifier, policy)
        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group policy assignment:", repr(e))
        return api_error("group policy assignment failed", 500)


@groups_blueprint.route(
        "/api/v2/groups/<int:identifier>/priority", methods=["POST"]
)
@check_permission(GROUP_RESOURCE, UPDATE_PERMISSION)
@deserialize_schema(schema_dataclass=AssignPriorityRequest,
                    key="priority_request")
def change_priority(identifier: int, priority_request: AssignPriorityRequest):
    """Change the priority of the group

    The priority controls which group will be applied to a device which is
    assigned to multiple groups.

    :param identifier: group identifier
    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to modify groups
    :status 404: the specified group does not exist
    :status 409: at least one device which is assigned to this group is also
    assigned to another group with the requested priority

    :<json int priority: new group priority to set

    **Example Request**

    .. sourcecode:: http

        POST /api/v2/groups/1/priority HTTP/1.1
        Content-Type: application/json
        Accept: application/json, text/javascript

        {
            "priority": 1,
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
    """
    try:
        if server.instance._groups_db.fetch_one(identifier) is None:
            return api_error("group does not exist", 404)

        priority: int = priority_request.priority
        err = server.instance._groups_db.update_priority(identifier, priority)
        if err is not None:
            return api_error(err, 409)

        return {}, 200
    except Exception as e:
        traceback.print_exc()
        print("Exception during group priority assignment:", repr(e))
        return api_error("group priority assignment failed", 500)
