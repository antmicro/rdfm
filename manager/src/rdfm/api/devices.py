import requests
import rdfm.config
from rdfm.api import wrap_api_error
from typing import List
from rdfm.schema.v1.devices import Device, Registration


def fetch_all(config: rdfm.config.Config) -> List[Device]:
    response = requests.get(
        rdfm.api.escape(config, "/api/v1/devices"),
        verify=config.ca_cert,
        auth=config.authorizer,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Server returned unexpected status code {response.status_code}"
        )

    groups: List[Device] = Device.Schema(many=True).load(response.json())
    return groups


def fetch_registrations(config: rdfm.config.Config) -> List[Registration]:
    response = requests.get(
        rdfm.api.escape(config, "/api/v1/auth/pending"),
        verify=config.ca_cert,
        auth=config.authorizer,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Server returned unexpected status code {response.status_code}"
        )

    registrations: List[Device] = Registration.Schema(many=True).load(
        response.json()
    )
    return registrations


def approve(config: rdfm.config.Config, mac: str, public_key: str):
    response = requests.post(
        rdfm.api.escape(config, "/api/v1/auth/register"),
        json={"mac_address": mac, "public_key": public_key},
        verify=config.ca_cert,
        auth=config.authorizer,
    )
    return wrap_api_error(response, "Approving device failed")
