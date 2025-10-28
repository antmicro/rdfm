from argparse import Namespace
from typing import Optional
from collections import namedtuple
from dataclasses import dataclass
import json
from jsonschema import validate
from rdfm_plotter.arguments import parse_args


Config = namedtuple("Config", "Consumer Keycloak")


consumer_config_schema = {
    "type": "object",
    "properties": {
        "bootstrap_servers": {"type": "string"},
        "ssl_cafile": {"type": "string"},
    },
}


keycloak_config_schema = {
    "type": "object",
    "properties": {
        "audience": {"type": "string"},
        "url": {"type": "string"},
        "client": {"type": "string"},
        "client_secret": {"type": "string"},
    },
}


def load_config(consumer_config: Optional[str] = None,
                keycloak_config: Optional[str] = None) -> Config:
    if consumer_config:
        with open(consumer_config) as f:
            c = json.loads(f.read())
            validate(instance=c, schema=consumer_config_schema)
    if keycloak_config:
        with open(keycloak_config) as f:
            k = json.loads(f.read())
            validate(instance=k, schema=keycloak_config_schema)

    return Config(ConsumerConfig(**c) if c else c, KeycloakConfig(**k) if k else k)


@dataclass
class ConsumerConfig:
    """
    Contains configuration fields for the Kafka consumer object.
    """
    bootstrap_servers: str
    ssl_cafile: str


@dataclass
class KeycloakConfig:
    """
    Contains configuration fields for the keycloak provider
    object facilitating OAUTH authentication.
    """
    audience: str
    url: str
    client: str
    client_secret: str


class ClientConfiguration(object):
    """
    A singleton object through which one should access the loaded or to-be loaded configuration.
    """
    _instance = None
    args: Namespace
    config: Config

    def __new__(cls) -> Config:
        if cls._instance is None:
            cls._instance = super(ClientConfiguration, cls).__new__(cls)
            cls._instance.args = parse_args()
            if not cls._instance.args.plain:
                cls._instance.config = load_config(cls._instance.args.consumer_config,
                                                   cls._instance.args.keycloak_config)
            elif not cls._instance.args.bootstrap_servers:
                cls._instance.config = load_config(cls._instance.args.consumer_config, None)

        return cls._instance
