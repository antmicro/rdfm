import re
import time
import configuration
from typing import Optional
from flask import current_app


from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc6749.wrappers import OAuth2Token
import kafka.errors as Errors
from kafka.admin import (
    KafkaAdminClient,
    NewTopic,
    ACL,
    ACLFilter,
    ACLOperation,
    ACLPermissionType,
    ResourcePattern,
    ResourceType,
)
from kafka.protocol.admin import CreateTopicsResponse_v3
from kafka.sasl.oauth import AbstractTokenProvider
from device_mgmt.pubsub_acl import (
    ACLTarget,
    RdfmDeviceWriteAuthorizationStatus,
    handle_acl_creation_result,
    handle_acl_deletion_result,
    device_mac_to_topic_name,
)


ADMIN_TIMEOUT_MS = 250


class KafkaAdminTokenProvider(AbstractTokenProvider):
    _token = Optional[OAuth2Token]
    _client_id: str
    _client_secret: str
    _token_endpoint: str
    _audience: str
    _cafile: Optional[str]
    _leeway: int

    def __init__(self,
                 client_id: str,
                 client_secret: str,
                 token_endpoint: str,
                 audience: str,
                 cacert: Optional[str] = None,
                 leeway: int = 30) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_endpoint = token_endpoint
        self._audience = audience
        self._token = None
        self._cacert = cacert
        self._leeway = leeway

    def token(self) -> str:
        if self._token and isinstance(self._token, OAuth2Token):
            if self._token["expires_at"] > time.time() + self._leeway:
                return self._token["access_token"]
        client = OAuth2Session(client_id=self._client_id, client_secret=self._client_secret)
        if self._cacert:
            client.verify = self._cacert
        self._token = client.fetch_token(self._token_endpoint,
                                         grant_type="urn:ietf:params:oauth:grant-type:uma-ticket",
                                         audience=self._audience)
        return self._token["access_token"]


class RdfmKafkaAdminClient(KafkaAdminClient):
    @classmethod
    def quick_create(cls):
        """
        A class method that quickly creates the RdfmKafkaAdminClient instance inheriting
        from KafkaAdminClient. It provides default arguments concering the way it connects
        to the cluster that fit the way it's used inside the RDFM management server.

        Returns:
            An already usable instance of RdfmKafkaTokenProvider.
        """
        conf: configuration.ServerConfig = current_app.config["RDFM_CONFIG"]

        # Here we assume that the Kafka configuration mirrors the way RDFM is set up.
        #   * If encryption is disabled, we expect Kafka and Keycloak to also not
        #     have encryption enabled.
        #   * If API auth is disabled, we expect Kafka to have auth disabled on the MGMT endpoint.
        #     Therefore Keycloak introspection won't be used for that endpoint.

        security_protocol = "PLAINTEXT"
        sasl_mechanism = None

        if conf.encrypted and not conf.disable_api_auth:
            security_protocol = "SASL_SSL"
            sasl_mechanism = "OAUTHBEARER"
        elif conf.encrypted:
            security_protocol = "SSL"  # SSL used but the Admin's principal will still be Anonymous
        elif not conf.disable_api_auth:
            security_ptocool = "SASL_PLAINTEXT"
            sasl_mechanism = "OAUTHBEARER"

        global _token_provider
        if not conf.disable_api_auth:
            if not _token_provider:
                _token_provider = KafkaAdminTokenProvider(conf.token_auth_client_id,
                                                          conf.token_auth_client_secret,
                                                          conf.token_auth_url,
                                                          conf.token_auth_audience,
                                                          cacert=(conf.cacert
                                                                  if conf.encrypted else None))

        return cls(bootstrap_servers=conf.mgmt_bootstrap_servers,
                   security_protocol=security_protocol,
                   sasl_mechanism=sasl_mechanism,
                   ssl_cafile=conf.cacert if conf.encrypted else None,
                   sasl_oauth_token_provider=_token_provider)

    def lease_topic_for_device(self, device_mac: str) -> str:
        """
        Creates a topic for the device client as well as assigns ACLs to that topic that
        permit the said device to write to it. If the topic already exists, this method
        will just make sure the ACLs are set correctly.

        Args:
            device_mac: MAC address of the device that should be leased a topic.

        Returns:
            The name of the topic that got assigned to the device client.
        """
        # Generate a topic_name from the given mac.
        # We do this because not all characters inside a MAC
        # address are valid for a topic name in Kafka.
        topic_name = device_mac_to_topic_name(device_mac)
        # Fetch information about the topic,
        # it's possible it already exists.
        topic_info = self.describe_topics([topic_name]).pop()

        create_topic_response = None
        err = Errors.for_code(topic_info["error_code"])
        match err:
            case Errors.UnknownTopicOrPartitionError:  # This indicates that no such topic exists
                # Create it then
                new_topic = NewTopic(topic_name,
                                     num_partitions=1,
                                     replication_factor=1)  # TODO: Optimize selecting these parameters # noqa: W291
                print(f"Trying to create a topic {topic_name}...")
                create_topic_response = self.create_topics([new_topic], timeout_ms=ADMIN_TIMEOUT_MS)

            case Errors.NoError:  # Topic already exists
                print("Topic already exists!")
                pass

            case _:  # Something unexpected happened!
                raise err(f"Failed to describe the {topic_name} topic!")

        # If we requested to create a topic, we also need
        # to check whether it was a successful operation.
        if create_topic_response:
            # Here we're forced to directly interact with the
            # protocol tuple if we want to know the details.
            # As of writing this, the response is v3.
            # If this assert ever starts failing, the new type should
            # be inspected for breaking changes and updated.
            assert type(create_topic_response) is CreateTopicsResponse_v3
            err = create_topic_response.topic_errors.pop()
            error_code = err[1]
            error_msg = err[2]
            if 0 != error_code:
                raise Errors.for_code(error_code)(error_msg)
            else:
                print(f"Successfully created topic {topic_name}!")

        if create_topic_response:
            # If create_topic_response isn't None it means that the topic was just
            # created, apply the neccesary ACLs immediately and skip other checks.
            print((f"Requesting to set ALLOW {device_mac} ACLs"
                   f" immediately for the topic {topic_name}..."))

            # Since the topic has just been created, we only pass the device
            # and topic names to status class
            status = RdfmDeviceWriteAuthorizationStatus.init_from_mac_and_topic_name(
                    device_mac,
                    topic_name)

            # Based on the given names, generate the necessary ACLs and apply them.
            result = self.create_acls(status.authorization_acls().add)

            exceptions = handle_acl_creation_result(result)
            if exceptions:  # If not None then the request failed
                raise exceptions
        else:
            print(f"Checking topic {topic_name} for existing ACLs...")
            acls = []
            for op in (ACLOperation.WRITE, ACLOperation.IDEMPOTENT_WRITE):
                acls += self._describe_acls_for_device(device_mac,
                                                       topic_name,
                                                       operation=op)
            status = (RdfmDeviceWriteAuthorizationStatus.init_from_acls(acls)
                      if acls else
                      # Covers edge case where a topic with no ACLs has been created manually before
                      RdfmDeviceWriteAuthorizationStatus.init_from_mac_and_topic_name(
                            device_mac,
                            topic_name,
                          )
                      )
            # Based on the possibly existing ACLs, generate the necessary ACLs
            # and apply them if there are any.
            target = status.authorization_acls()
            if target.add:
                result = self.create_acls(target.add)
                exceptions = handle_acl_creation_result(result)
                if exceptions:  # If not None then the request failed
                    raise exceptions
            if target.delete:
                result = self.delete_acls(target.delete)
                exceptions = handle_acl_deletion_result(result)
                if exceptions:  # If not None then the request failed
                    raise exceptions

        return topic_name  # Now this topic can be safely given to the to-be consumer

    def confiscate_topic_from_device(self, device_mac: str) -> None:
        """
        Stops a device from being able to write to its topic.

        Args:
            device_mac: MAC address of the device whose topic should be confiscated.
        """
        topic_name = device_mac_to_topic_name(device_mac)
        topic_info = self.describe_topics([topic_name]).pop()

        err = Errors.for_code(topic_info["error_code"])
        match err:
            case Errors.UnknownTopicOrPartitionError:
                raise err(f"Cannot deauthorize {device_mac}: topic {topic_name} doesn't exist")
            case Errors.NoError:
                pass
            case _:
                raise err(("Failed to deauthorize"
                           f" {device_mac}: cannot describe {topic_name}"))

        print(f"Checking topic {topic_name} for existing ACLs...")
        acls = []
        for op in (ACLOperation.WRITE, ACLOperation.IDEMPOTENT_WRITE):
            acls += self._describe_acls_for_device(device_mac,
                                                   topic_name,
                                                   operation=op)
        status = RdfmDeviceWriteAuthorizationStatus.init_from_acls(acls)
        target = status.deauthorization_acls()
        # Here we're only adding ACLs because DENY shadows ALLOW ACLs,
        # so as long as there are DENY ACLs, the ALLOW ones don't matter.
        if target.add:
            result = self.create_acls(target.add)
            exceptions = handle_acl_creation_result(result)
            if exceptions:  # If not None then the request failed
                raise exceptions

    def device_topic_status(
            self,
            device_mac: str
            ) -> Optional[RdfmDeviceWriteAuthorizationStatus]:
        """
        Fetches information about a device's topic.

        Args:
            device_mac: MAC address of the device whose topic you want to inspect.

        Returns:
            An instance of RdfmDeviceWriteAuthorizationStatus if the device's topic exists.
        """
        topic_name = device_mac_to_topic_name(device_mac)
        topic_info = self.describe_topics([topic_name]).pop()

        err = Errors.for_code(topic_info["error_code"])
        match err:
            case Errors.UnknownTopicOrPartitionError:
                return None  # Topic for the given device doesn't exist
            case Errors.NoError:
                pass
            case _:
                raise err(("Failed to check authorization status of"
                           f" {device_mac}: cannot describe {topic_name}"))
        acls = []
        for op in (ACLOperation.WRITE, ACLOperation.IDEMPOTENT_WRITE):
            acls += self._describe_acls_for_device(device_mac,
                                                   topic_name,
                                                   operation=op)
        return RdfmDeviceWriteAuthorizationStatus.init_from_acls(acls)

    def _describe_acls_for_device(self,
                                  device_mac: str,
                                  topic: str,
                                  host: str = "*",
                                  operation: ACLOperation = ACLOperation.ANY,
                                  permission_type: ACLPermissionType = ACLPermissionType.ANY):
        """
        A utility wrapper method that simplifies fetching LITERAL ACLs from the cluster.

        Args:
            device_mac: MAC address of the device whose ACLs are to be fetched.
            topic: LITERAL topic name of the ACLs that are to be fetched.
            host: Host's name/address of the ACLs that are to be fetched. Wildcard by default.
            operation: The operation of the ACLs that are to be fetched. ANY by default.
            permission_type. The permission type of the ACLs that are to be fetched. ANY by default.

        Returns:
            ACL objects that match the specified properties.
        """
        acls, err = self.describe_acls(
            ACLFilter(
                principal=f"User:{device_mac}",
                host=host,
                operation=operation,
                permission_type=permission_type,
                resource_pattern=ResourcePattern(
                    ResourceType.TOPIC,
                    topic
                )  # Implicitly LITERAL pattern type
            )
        )
        if err is not Errors.NoError:
            raise error
        return acls


"""Global instance of the token provider
"""
_token_provider: Optional[KafkaAdminTokenProvider] = None
