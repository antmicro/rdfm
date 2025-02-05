from flask import Blueprint
import models.permission
from rdfm.schema.v1.permission import Permission
from api.v1.common import (
    api_error,
    wrap_api_exception,
)
from api.v1.middleware import (
    management_user_validation,
    management_read_only_api,
    management_read_write_api,
    deserialize_schema,
    check_admin_rights,
    authenticated_api
)
from typing import List, Optional
import server
import datetime

permissions_blueprint: Blueprint = Blueprint(
    "rdfm-server-permissions", __name__)


def model_to_schema(
    permission: models.permission.Permission
) -> Permission:
    """Convert a database permission model to a schema model.
    """
    return Permission(
        id=permission.id,
        resource=permission.resource,
        created=permission.created,
        user_id=permission.user_id,
        resource_id=permission.resource_id,
        permission=permission.permission,
    )


@permissions_blueprint.route("/api/v1/permissions")
@authenticated_api
@wrap_api_exception("permissions fetching failed")
def fetch_all(**kwargs):
    """Fetch all permissions 

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to read permissions

    :>jsonarr string created: UTC creation date (RFC822)
    :>jsonarr integer id: permission identifier
    :>jsonarr str permission: permission type (read/update/delete)
    :>jsonarr str resource: type of resource (group/device/package)
    :>jsonarr str user_id: id of the user to whom this permission applies
    :>jsonarr integer resource_id: id of the resource to which this permission applies

    **Example Request**

    .. sourcecode:: http

        GET /api/v1/permissions HTTP/1.1
        Accept: application/json

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            { 
                "created": "Thu, 16 Jan 2025 13:31:53 -0000",
                "id": 1,
                "permission": "read",
                "resource": "group",
                "resource_id": 2,
                "user_id": "095e4160-9017-4868-82a5-fe0a0c44d34c"
            }
        ]
    """  # noqa: E501

    has_admin_rights = check_admin_rights(kwargs.get('user_roles', []), True)
    user_id = kwargs.get('user_id') if not has_admin_rights else None

    permissions: List[
        models.permission.
        Permission] = server.instance._permissions_db.fetch_all(user_id=user_id)
    return Permission.Schema().dump([
        model_to_schema(perms) for perms in permissions
    ], many=True), 200


@permissions_blueprint.route("/api/v1/permissions", methods=["POST"])
@management_read_write_api
@wrap_api_exception("permission creation failed")
@deserialize_schema(schema_dataclass=Permission, key="perm")
def create(perm: Permission):
    """Create a new permission

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to create permissions

    **Example Request**

    .. sourcecode:: http

        POST /api/v1/permissions HTTP/1.1
        Content-Type: application/json
        Accept: application/json

        {
            "resource": "group",
            "resource_id": 5,
            "user_id": "095e4160-9017-4868-82a5-fe0a0c44d34c",
            "permission": "read"
        }

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "created": "Thu, 23 Jan 2025 13:03:44 -0000",
            "id": 26,
            "permission": "read",
            "resource": "group",
            "resource_id": 5,
            "user_id": "095e4160-9017-4868-82a5-fe0a0c44d34c"
        }

    """  # noqa: E501

    permission = models.permission.Permission()
    permission.created = datetime.datetime.utcnow()
    permission.resource = perm.resource
    permission.user_id = perm.user_id
    permission.resource_id = perm.resource_id
    permission.permission = perm.permission

    err = server.instance._permissions_db.create(permission)

    if err is not None:
        return api_error(err, 409)

    return Permission.Schema().dump(
        model_to_schema(permission)), 200


@permissions_blueprint.route("/api/v1/permissions/<int:identifier>")
@management_read_write_api
@wrap_api_exception("permission fetching failed")
def fetch_one(identifier: int):
    """Fetch permission

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to read permissions

    **Example Request**

    .. sourcecode:: http

        GET /api/v1/permissions/26 HTTP/1.1
        Accept: application/json

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        
        {
            "created": "Thu, 23 Jan 2025 13:03:44 -0000",
            "id": 26,
            "permission": "read",
            "resource": "group", 
            "resource_id": 5,
            "user_id": "095e4160-9017-4868-82a5-fe0a0c44d34c"
        }
    """  # noqa: E501

    permission: Optional[
        models.permission.Permission
    ] = server.instance._permissions_db.fetch_one(identifier)
    if permission is None:
        return api_error("resource does not exist", 404)
    return Permission.Schema().dump(
        model_to_schema(permission)), 200


@permissions_blueprint.route("/api/v1/permissions/<int:identifier>",
                             methods=["DELETE"])
@management_read_write_api
@wrap_api_exception("permission deletion failed")
def delete_one(identifier: int):
    """Delete permission

    :status 200: no error
    :status 401: user did not provide authorization data,
                 or the authorization has expired
    :status 403: user was authorized, but did not have permission
                 to delete permissions

    **Example Request**

    .. sourcecode:: http

        DELETE /api/v1/permissions/26 HTTP/1.1

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {}
    """

    permission: Optional[
        models.permission.Permission
    ] = server.instance._permissions_db.fetch_one(identifier)
    if permission is None:
        return api_error("permission does not exist", 404)

    success = server.instance._permissions_db.delete(identifier)
    if not success:
        return api_error("permission deletion wasn't successful", 409)

    return {}, 200
