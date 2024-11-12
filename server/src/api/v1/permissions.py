from flask import Blueprint
import models.permission
from rdfm.schema.v1.permission import Permission
from api.v1.common import (
    api_error,
    wrap_api_exception,
)
from api.v1.middleware import (
    management_read_only_api,
    management_read_write_api,
    deserialize_schema,
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
@management_read_only_api
@wrap_api_exception("permissions fetching failed")
def fetch_all():
    """Fetch all permissions
    """
    permissions: List[
        models.permission.
        Permission] = server.instance._permissions_db.fetch_all(
        )
    return Permission.Schema().dump([
        model_to_schema(perms) for perms in permissions
    ], many=True), 200


@permissions_blueprint.route("/api/v1/permissions", methods=["POST"])
@management_read_write_api
@wrap_api_exception("permission creation failed")
@deserialize_schema(schema_dataclass=Permission, key="perm")
def create(perm: Permission):
    """Create a new permission
    """
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
    """
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
