import requests
import rdfm.config
from rdfm.api import wrap_api_error
from typing import List, Optional
from rdfm.schema.v1.permission import Permission


def fetch_all(config: rdfm.config.Config) -> List[Permission]:
    response = requests.get(
        rdfm.api.escape(config, "/api/v1/permissions"),
        verify=config.ca_cert,
        auth=config.authorizer,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Server returned unexpected status code {response.status_code}"
        )

    permissions: List[Permission] = (Permission.Schema(many=True)
                                     .load(response.json()))
    return permissions


def add_permission(config: rdfm.config.Config, resource: str, resource_id: int,
                   user_id: str, permission: str) -> Optional[str]:
    response = requests.post(
        rdfm.api.escape(config, "/api/v1/permissions"),
        json={
            "resource": resource, "resource_id": resource_id,
            "user_id": user_id, "permission": permission
        },
        verify=config.ca_cert,
        auth=config.authorizer,
    )
    return wrap_api_error(response, "Adding permission failed")


def remove_permission(config: rdfm.config.Config,
                      permission_id: int) -> Optional[str]:
    response = requests.delete(rdfm.api.escape(config,
                               f"/api/v1/permissions/{permission_id}"),
                               verify=config.ca_cert,
                               auth=config.authorizer)
    return wrap_api_error(response, "Removing permission failed")
