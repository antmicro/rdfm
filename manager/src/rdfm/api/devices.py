import datetime
import requests
import rdfm.config
from dataclasses import dataclass, field
from rdfm.api import wrap_api_error
from typing import List, Any, Optional, Callable
import marshmallow_dataclass


@dataclass
class Device():
    """ Represents the data of a device
    """
    id: int = field(metadata={
        "required": True
    })
    name: str = field(metadata={
        "required": True
    })
    mac_address: str = field(metadata={
        "required": True
    })
    capabilities: dict[str, bool] = field(metadata={
        "required": True
    })
    metadata: dict[str, str] = field(metadata={
        "required": True
    })
    group: Optional[int] = field(metadata={
        "required": True,
        "allow_none": True
    })
    last_access: Optional[datetime.datetime] = field(metadata={
        "required": True,
        "allow_none": True,
        "format": "rfc"
    })
    public_key: str = field(metadata={
        "required": True,
        "allow_none": True
    })


@dataclass
class Registration():
    """ Represents a registration request
    """
    mac_address: str = field(metadata={
        "required": True
    })
    public_key: str = field(metadata={
        "required": True
    })
    metadata: dict[str, str] = field(metadata={
        "required": True
    })
    last_appeared: datetime.datetime = field(metadata={
        "required": True,
        "format": "rfc"
    })


DeviceSchema = marshmallow_dataclass.class_schema(Device)
RegistrationSchema = marshmallow_dataclass.class_schema(Registration)


def fetch_all(config: rdfm.config.Config) -> List[Device]:
    response = requests.get(rdfm.api.escape(config, "/api/v1/devices"),
                            cert=config.ca_cert,
                            auth=config.authorizer)
    if response.status_code != 200:
        raise RuntimeError(f"Server returned unexpected status code {response.status_code}")

    groups: List[Device] = DeviceSchema(many=True).load(response.json())
    return groups


def fetch_registrations(config: rdfm.config.Config) -> List[Registration]:
    response = requests.get(rdfm.api.escape(config, "/api/v1/auth/pending"),
                            cert=config.ca_cert,
                            auth=config.authorizer)
    if response.status_code != 200:
        raise RuntimeError(f"Server returned unexpected status code {response.status_code}")

    registrations: List[Device] = RegistrationSchema(many=True).load(response.json())
    return registrations


def approve(config: rdfm.config.Config,
            mac: str,
            public_key: str):
    response = requests.post(rdfm.api.escape(config, "/api/v1/auth/register"),
                             json={
                                "mac_address": mac,
                                "public_key": public_key
                             },
                             cert=config.ca_cert,
                             auth=config.authorizer)
    return wrap_api_error(response, "Approving device failed")
