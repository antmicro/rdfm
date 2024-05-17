import requests
import rdfm.config
from typing import List, Any, Optional
from rdfm.api import wrap_api_error
from rdfm.schema.v2.groups import Group
from rdfm.schema.v1.error import ApiError


def fetch_all(config: rdfm.config.Config) -> List[Group]:
    response = requests.get(
        rdfm.api.escape(config, "/api/v2/groups"),
        verify=config.ca_cert,
        auth=config.authorizer,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Server returned unexpected status code {response.status_code}"
        )

    groups: List[Group] = Group.Schema(many=True).load(response.json())
    return groups


def create(
        config: rdfm.config.Config, metadata: dict[str, Any], priority: int
) -> Optional[str]:
    req_json = {"metadata": metadata}
    if priority is not None:
        req_json["priority"] = priority
    response = requests.post(rdfm.api.escape(config, "/api/v2/groups"),
                             verify=config.ca_cert,
                             auth=config.authorizer,
                             json=req_json)

    if response.status_code == 200:
        try:
            print(f"Created group with identifier #{response.json()['id']}")
        except requests.exceptions.JSONDecodeError:
            print("Created group (could not retrieve identifier)")
    return wrap_api_error(response, "Creating group failed")


def delete(config: rdfm.config.Config, id: int) -> Optional[str]:
    response = requests.delete(
        rdfm.api.escape(config, f"/api/v2/groups/{id}"),
        verify=config.ca_cert,
        auth=config.authorizer,
    )
    if response.status_code == 409:
        return (
            "Deleting group failed: some devices are still assigned to "
            "the group, deletion is impossible"
        )
    return wrap_api_error(response, "Deleting group failed")


def assign(
    config: rdfm.config.Config, group: int, packages: List[int]
) -> Optional[str]:
    response = requests.post(
        rdfm.api.escape(config, f"/api/v2/groups/{group}/package"),
        verify=config.ca_cert,
        auth=config.authorizer,
        json={"packages": packages},
    )
    if response.status_code == 409:
        return (
            "Assigning package failed: there was a conflict during the "
            "operation, the package may have already been removed from "
            "the server"
        )
    return wrap_api_error(response, "Assigning package failed")


def assign_device(
    config: rdfm.config.Config,
    group: int,
    insertions: List[str],
    removals: List[str],
) -> Optional[str]:
    response = requests.patch(
        rdfm.api.escape(config, f"/api/v2/groups/{group}/devices"),
        verify=config.ca_cert,
        auth=config.authorizer,
        json={"add": insertions, "remove": removals},
    )

    if response.status_code == 409:
        try:
            error: ApiError = ApiError.Schema().load(response.json())
            return f"Assigning device failed: {error.error}"
        except requests.exceptions.JSONDecodeError:
            return "Assigning device failed: a conflict has occurred"
    return wrap_api_error(response, "Assigning device failed")


def set_policy(
    config: rdfm.config.Config, group: int, policy: str
) -> Optional[str]:
    response = requests.post(
        rdfm.api.escape(config, f"/api/v2/groups/{group}/policy"),
        verify=config.ca_cert,
        auth=config.authorizer,
        json={
            "policy": policy,
        },
    )
    return wrap_api_error(response, "Updating group policy failed")


def set_priority(config: rdfm.config.Config,
                 group: int,
                 priority: int) -> Optional[str]:
    response = requests.post(
        rdfm.api.escape(config, f"/api/v2/groups/{group}/priority"),
        verify=config.ca_cert,
        auth=config.authorizer,
        json={
            "priority": priority,
            }
     )
    return wrap_api_error(response, "Updating group priority failed")
