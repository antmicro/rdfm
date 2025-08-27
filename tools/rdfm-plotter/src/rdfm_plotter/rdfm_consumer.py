from kafka import KafkaConsumer
from dataclasses import asdict
from typing import Optional
from rdfm_plotter.config import ClientConfiguration
from rdfm_plotter.keycloak_token_provider import KeycloakTokenProvider
from rdfm_plotter.utils import consumer_seek_hours_delta


def try_create_keycloak_token_provider() -> Optional[KeycloakTokenProvider]:
    """
    Create the KeycloakTokenProvider if the ClientConfiguration is instantiated.
    """
    if ClientConfiguration() is None:
        return None
    return KeycloakTokenProvider(ClientConfiguration().config.Keycloak.client,
                                 ClientConfiguration().config.Keycloak.client_secret,
                                 ClientConfiguration().config.Keycloak.url,
                                 ClientConfiguration().config.Keycloak.audience)


class RdfmConsumer(KafkaConsumer):
    """
    Class inheriting from `KafkaConsumer` with defaults tailored to RDFM's current use case.
    """
    @classmethod
    def quick_create(cls):
        """
        Create a SASL_SSL consumer with the OAUTHBEARER mechanism. Topic and bootstrap
        servers are determined by the contents of the ClientConfiguration singleton.
        This method also respects the `--offset-hours` argument that shifts all the offsets
        to a predetermined time before returning a consumer object.
        """
        instance = cls(ClientConfiguration().args.topic,
                       security_protocol="SASL_SSL",
                       sasl_mechanism="OAUTHBEARER",
                       sasl_oauth_token_provider=try_create_keycloak_token_provider(),
                       **asdict(ClientConfiguration().config.Consumer))

        if ClientConfiguration().args.offset_hours != 0.0:
            consumer_seek_hours_delta(instance)

        return instance
