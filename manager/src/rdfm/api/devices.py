import requests
import rdfm.config
from rdfm.api import wrap_api_error
from typing import List
from rdfm.schema.v2.devices import Device, Registration


def fetch_all(config: rdfm.config.Config) -> List[Device]:
    response = requests.get(
        rdfm.api.escape(config, "/api/v2/devices"),
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


def remove_registered(config: rdfm.config.Config,
                      identifier: int):
    response = requests.delete(rdfm.api.escape(config,
                               f"/api/v1/devices/{identifier}"),
                               verify=config.ca_cert,
                               auth=config.authorizer)
    return wrap_api_error(response, "Removing device failed")


def remove_pending(config: rdfm.config.Config,
                   mac_address: str, public_key: str):
    response = requests.delete(rdfm.api.escape(config, "/api/v1/auth/pending"),
                               json={"mac_address": mac_address,
                                     "public_key": public_key},
                               verify=config.ca_cert,
                               auth=config.authorizer)
    return wrap_api_error(response, "Removing device failed")


def download_file(config: rdfm.config.Config,
                  device: str, file: str):
    response = requests.post(rdfm.api.escape(config,
                             f"/api/v2/devices/{device}/fs/file"),
                             json={"file": file},
                             verify=config.ca_cert,
                             auth=config.authorizer)

    if response.status_code != 200:
        raise RuntimeError(
            f"Server returned unexpected status code {response.status_code}"
        )

    return response.json()
