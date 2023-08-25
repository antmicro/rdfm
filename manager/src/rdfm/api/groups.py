import json
import datetime
import requests
import rdfm.config
from typing import List, Any, Optional, Callable
from types import SimpleNamespace
from rdfm.api import wrap_api_error
from marshmallow import Schema, fields, post_load


class Group():
    id: int
    created: datetime.datetime
    devices: list[int]
    package_id: Optional[int]
    metadata: dict[str, Any]

    def __init__(self, id, created, devices, package_id, metadata):
        self.id = id
        self.created = created
        self.devices = devices
        self.package_id = package_id
        self.metadata = metadata


class GroupSchema(Schema):
    """ Group schema, as returned by the API
    """
    id = fields.Int(required=True)
    created = fields.DateTime(required=True, format="rfc")
    devices = fields.List(fields.Int,
                          required=True)
    package_id = fields.Int(required=True,
                            allow_none=True)
    metadata = fields.Dict(keys=fields.Str(),
                           values=fields.Str(),
                           required=True)

    @post_load
    def make_group(self, data, **kwargs):
        return Group(**data)


def fetch_all(config: rdfm.config.Config) -> List[Group]:
    response = requests.get(rdfm.api.escape(config, "/api/v1/groups"),
                            cert=config.ca_cert,
                            auth=config.authorizer)
    if response.status_code != 200:
        raise RuntimeError(f"Server returned unexpected status code {response.status_code}")

    groups: List[Group] = GroupSchema(many=True).load(response.json())
    return groups


def create(config: rdfm.config.Config, metadata: dict[str, Any]) -> Optional[str]:
    response = requests.post(rdfm.api.escape(config, "/api/v1/groups"),
                             cert=config.ca_cert,
                             auth=config.authorizer,
                             json=metadata)
    if response.status_code == 200:
        try:
            print(f"Created group with identifier #{response.json()['id']}")
        except:
            print(f"Created group (could not retrieve identifier)")
    return wrap_api_error(response, "Creating group failed")


def delete(config: rdfm.config.Config, id: int) -> Optional[str]:
    response = requests.delete(rdfm.api.escape(config, f"/api/v1/groups/{id}"),
                               cert=config.ca_cert,
                               auth=config.authorizer)
    if response.status_code == 409:
        return "Deleting group failed: some devices are still assigned to the group, deletion is impossible"
    return wrap_api_error(response, "Deleting group failed")


def assign(config: rdfm.config.Config, group: int, package: Optional[int]) -> Optional[str]:
    response = requests.post(rdfm.api.escape(config, f"/api/v1/groups/{group}/package"),
                             cert=config.ca_cert,
                             auth=config.authorizer,
                             json={
                                 "package_id": package
                             })
    if response.status_code == 409:
        return ("Assigning package failed: there was a conflict during the operation,"
               "the package may have already been removed from the server")
    return wrap_api_error(response, "Assigning package failed")


def assign_device(config: rdfm.config.Config,
                  group: int,
                  insertions: List[str],
                  removals: List[str]) -> Optional[str]:
    response = requests.patch(rdfm.api.escape(config, f"/api/v1/groups/{group}/devices"),
                              cert=config.ca_cert,
                              auth=config.authorizer,
                              json={
                                  "add": insertions,
                                  "remove": removals
                              })

    if response.status_code == 409:
        try:
            return f'Assigning device failed: {response.json()["error"]}'
        except:
            return "Assigning device failed: a conflict has occured"
    return wrap_api_error(response, "Assigning device failed")
