import re
from dataclasses import dataclass, field
from typing import Optional
import kafka.errors as Errors
from kafka.admin import (
    ACL,
    ACLFilter,
    ACLOperation,
    ACLPermissionType,
    ResourcePattern,
    ACLResourcePatternType,
    ResourceType,
)


@dataclass
class ACLTarget:
    """
    A dataclass describing what ACLs are to be added/deleted.
    """
    add: list[ACL] = field(default_factory=list)
    delete: list[ACLFilter] = field(default_factory=list)


@dataclass
class RdfmDeviceWriteAuthorizationStatus:
    """
    A dataclass denoting what WRITE ACLs are set for a device on a topic.
    It contains methods that generate an instance of ACLTarget based on its current
    state and the requested state. Then the ACLTarget's members can be used to alter
    the ACLs.
    """
    principal: Optional[str] = None
    topic_name: Optional[str] = None
    host: str = "*"

    allow_write: bool = False
    deny_write: bool = False

    allow_idempotent_write: bool = False
    deny_idempotent_write: bool = False

    @classmethod
    def init_from_mac_and_topic_name(cls, device_mac: str, topic_name: str):
        """
        This method should be called when the topic has just been created or has no ACLs.
        """
        status = cls()
        status.principal = f"User:{device_mac}"
        status.topic_name = topic_name
        return status

    @classmethod
    def init_from_acls(cls, acls: list[ACL] = []):
        """
        This method initializes this dataclass to the state denoted by the given ACLs.
        """
        status = cls()
        # In case of an empty list we just restore the class to its initial state.
        if 0 == len(acls):
            status.principal = None
            status.topic_name = None
            status.host = "*"
            status.allow_write = False
            status.deny_write = False
            status.allow_idempotent_write = False
            status.deny_idempotent_write = False
            return status

        # First of all, ensure that each ACL has the same principal.
        # It doesn't make sense to load from ACLs describing multiple principals.
        same = all(acls[0].principal == acl.principal for acl in acls)
        if not same:
            raise ValueError("All principals in the ACL list must be the same")
        status.principal = acls[0].principal

        # Secondly, every ACL needs to concern the same resource type -- a topic.
        is_resource_type_topic = all(
                ResourceType.TOPIC == acl.resource_pattern.resource_type for acl in acls
        )
        if not is_resource_type_topic:
            raise ValueError(
                    "All resource types in the ACL list must be of type ResourceType.TOPIC"
            )

        # Also, that resource has to actually describe a
        # concrete topic, not a pattern or a wildcard.
        is_pattern_type_literal = all(
                ACLResourcePatternType.LITERAL == acl.resource_pattern.pattern_type
                for acl in acls
        )
        if not is_pattern_type_literal:
            raise ValueError(
                    "All pattern types in the ACL list must"
                    " be of type ACLResourcePatternType.LITERAL"
            )

        # Ensure that each ACL has the same topic name associated with it as well.
        # It doesn't make sense to load from ACLs concering multiple topics.
        same = all(
                acls[0].resource_pattern.resource_name == acl.resource_pattern.resource_name
                for acl in acls
        )
        if not same:
            raise ValueError("All topics in the ACL list must be the same")
        status.topic_name = acls[0].resource_pattern.resource_name

        # Now that we're sure that each ACL in the list is consistent content-wise,
        # we can iterate and populate the boolean flags with the correct values
        # based on what is seen.
        for acl in acls:
            match acl.permission_type:
                case ACLPermissionType.ALLOW:
                    match acl.operation:
                        case ACLOperation.WRITE:
                            status.allow_write = True
                        case ACLOperation.IDEMPOTENT_WRITE:
                            status.allow_idempotent_write = True
                case ACLPermissionType.DENY:
                    match acl.operation:
                        case ACLOperation.WRITE:
                            status.deny_write = True
                        case ACLOperation.IDEMPOTENT_WRITE:
                            status.deny_idempotent_write = True
        return status

    def can_write(self) -> bool:
        """
        Returns True if the current state indicates that the device can write.
        """
        return self.allow_write and not self.deny_write

    def can_idempotent_write(self) -> bool:
        """
        Returns True if the current state indicates that the device can idempotently write.
        """
        return self.allow_idempotent_write and not self.deny_idempotent_write

    def authorization_acls(self) -> Optional[ACLTarget]:
        """
        Returns and instance of ACLTarget that describes what ACLs should be added/deleted
        to achieve an authorized state for the device.

        If the state isn't set up correctly via an init method it returns None.
        """
        if not self.principal or not self.topic_name:
            # All the dataclass fields should be populated
            # with a init method before running this
            return None

        target = ACLTarget()
        pattern = ResourcePattern(ResourceType.TOPIC, self.topic_name)  # LITERAL by default
        if not self.allow_write:
            target.add.append(ACL(principal=self.principal,
                                  host=self.host,
                                  operation=ACLOperation.WRITE,
                                  permission_type=ACLPermissionType.ALLOW,
                                  resource_pattern=pattern))
        if not self.allow_idempotent_write:
            target.add.append(ACL(principal=self.principal,
                                  host=self.host,
                                  operation=ACLOperation.IDEMPOTENT_WRITE,
                                  permission_type=ACLPermissionType.ALLOW,
                                  resource_pattern=pattern))
        if self.deny_write:
            target.delete.append(ACLFilter(principal=self.principal,
                                           host=self.host,
                                           operation=ACLOperation.WRITE,
                                           permission_type=ACLPermissionType.DENY,
                                           resource_pattern=pattern))
        if self.deny_idempotent_write:
            target.delete.append(ACLFilter(principal=self.principal,
                                           host=self.host,
                                           operation=ACLOperation.IDEMPOTENT_WRITE,
                                           permission_type=ACLPermissionType.DENY,
                                           resource_pattern=pattern))
        return target

    def deauthorization_acls(self) -> Optional[ACLTarget]:
        """
        Returns and instance of ACLTarget that describes what ACLs should be added/deleted
        to achieve an unauthorized state for the device.

        If the state isn't set up correctly via an init method it returns None.
        """
        if not self.principal or not self.topic_name:
            # All the dataclass fields should be populated
            # with a init method before running this
            return None

        target = ACLTarget()
        pattern = ResourcePattern(ResourceType.TOPIC, self.topic_name)  # LITERAL by default
        if not self.deny_write:
            target.add.append(ACL(principal=self.principal,
                                  host=self.host,
                                  operation=ACLOperation.WRITE,
                                  permission_type=ACLPermissionType.DENY,
                                  resource_pattern=pattern))
        if not self.deny_idempotent_write:
            target.add.append(ACL(principal=self.principal,
                                  host=self.host,
                                  operation=ACLOperation.IDEMPOTENT_WRITE,
                                  permission_type=ACLPermissionType.DENY,
                                  resource_pattern=pattern))
        return target


def handle_acl_creation_result(result: dict) -> Optional[ExceptionGroup]:
    """
    According to the kafka-python's KafkaAdmin.create_acls docstring,
    this is the structure of the result dictionary:
         {
           'succeeded': [list of ACL objects successfully created],
           'failed': [(acl_object, KafkaError), ...]
         }

    This function extracts the exceptions if there are any.
    If every ACL creation succeeded, then it returns None.
    """
    if 0 == len(result["failed"]):
        return None  # Everything succeeded

    # We iterate over every exception and initalize it inside
    # the list to the be KafkaError(repr(acl_object))
    exceptions = ExceptionGroup(f"{len(result['failed'])} ACL creation(s) failed",
                                [
                                    r[1](r[0])
                                    for r in result["failed"]
                                ])
    return exceptions


def handle_acl_deletion_result(result: list[tuple[ACLFilter, list[tuple[ACL, Errors.KafkaError]], Errors.KafkaError]]) -> Optional[ExceptionGroup]:  # noqa: E501
    """
    According to the kafka-python's `KafkaAdmin.delete_acls` docstring,
    this is the structure of the resulting list member tuple:
        (acl_filter, [(matching_acl, KafkaError), ...], filter_level_error).

    This helper function extracts the exceptions if there are any.
    If every ACL deletion succeeded, then it returns None.
    """
    def handle_partial(filter: ACLFilter,
                       partial_result: list[tuple[ACL, Errors.KafkaError]]) -> Optional[ExceptionGroup]:  # noqa: E501
        exceptions = []
        for p in partial_result:
            if p[1] is not Errors.NoError:
                exceptions.append(p[1](p[0]))
        if exceptions:
            return ExceptionGroup(
                    f"Encountered failure(s) during deleting with {filter}",
                    exceptions)
        else:
            return None

    exceptions = []
    for r in result:
        if r[2] is not Errors.NoError:
            exceptions.append(r[2](r[0]))
        partial = handle_partial(r[0], r[1])
        if partial:
            exceptions.append(partial)
    if exceptions:
        return ExceptionGroup(
                f"Encountered failure(s) during ACL deletion",
                exceptions)
    else:
        return None


def device_mac_to_topic_name(device_mac: str) -> str:
    """
    Legal characters for a topic are are: [a-zA-Z0-\._\-]
    This function replaces all illegal characters with a hyphen.
    """  # noqa: W291
    return re.sub("[^a-zA-Z0-9\\._\\-]", "-", device_mac)
