import pytest
import kafka.errors as Errors
from device_mgmt.pubsub_acl import (
    ACLTarget,
    RdfmDeviceWriteAuthorizationStatus,
    handle_acl_creation_result,
    handle_acl_deletion_result,
    device_mac_to_topic_name,
)
from kafka.admin import (
    ACL,
    ACLFilter,
    ACLOperation,
    ACLPermissionType,
    ACLResourcePatternType,
    ResourcePattern,
    ResourceType,
)


MAC = "00:00:00:00:00:00"
ZERO_ADD = "There should be no need for ACL additions"
ZERO_DEL = "There should be no need for ACL deletions"
TWO_ADD = "There should be 2 required ACLs to be added"
TWO_DEL = "There should be 2 required ACLs to be deleted"


# Helper functions


def create_write_acls(device_mac: str, permission_type: ACLPermissionType) -> list[ACL]:
    acls = []
    topic_name = device_mac_to_topic_name(device_mac)
    for op in (ACLOperation.WRITE, ACLOperation.IDEMPOTENT_WRITE):
        acls.append(ACL(principal=f"User:{device_mac}",
                        host="*",
                        operation=op,
                        permission_type=permission_type,
                        resource_pattern=ResourcePattern(ResourceType.TOPIC, topic_name)))
    return acls


def create_filter_and_acls(device_mac: str, permission_type: ACLPermissionType) -> tuple[ACLFilter, list[ACL]]:
    acls = create_write_acls(device_mac, ACLPermissionType.DENY)
    filter = ACLFilter(principal=f"User:{device_mac}",
                       host="*",
                       operation=ACLOperation.ANY,
                       permission_type=permission_type,
                       resource_pattern=ResourcePattern(ResourceType.TOPIC, device_mac_to_topic_name(device_mac)))
    return (filter, acls)


# RdfmDeviceWriteAuthorizationStatus tests


def test_load_allow_write_acls():
    status = RdfmDeviceWriteAuthorizationStatus.init_from_acls(
            create_write_acls(
                MAC,
                ACLPermissionType.ALLOW
            )
    )

    assert status.can_write() and status.can_idempotent_write(), (
            "Loaded ACLs should indicate that the device can write")

    target = status.authorization_acls()
    assert 0 == len(target.add), ZERO_ADD
    assert 0 == len(target.delete), ZERO_DEL

    target = status.deauthorization_acls()
    assert 2 == len(target.add), TWO_ADD
    assert 0 == len(target.delete), ZERO_DEL


def test_load_deny_write_acls():
    status = RdfmDeviceWriteAuthorizationStatus.init_from_acls(
            create_write_acls(
                MAC,
                ACLPermissionType.DENY
            )
    )

    assert not status.can_write() and not status.can_idempotent_write(), (
            "Loaded ACLs should indicate that the device can't write")

    target = status.authorization_acls()
    assert 2 == len(target.add), TWO_ADD
    assert 2 == len(target.delete), TWO_DEL

    target = status.deauthorization_acls()
    assert 0 == len(target.add), ZERO_ADD
    assert 0 == len(target.delete), ZERO_DEL


def test_load_allow_and_deny_write_acls():
    acls = (create_write_acls(MAC, ACLPermissionType.ALLOW)
            + create_write_acls(MAC, ACLPermissionType.DENY))
    status = RdfmDeviceWriteAuthorizationStatus.init_from_acls(acls)

    assert not status.can_write() and not status.can_idempotent_write(), (
            "Loaded ACLs should indicate that the device can't write")

    target = status.authorization_acls()
    assert 0 == len(target.add), ZERO_ADD
    assert 2 == len(target.delete), TWO_DEL

    target = status.deauthorization_acls()
    assert 0 == len(target.add), ZERO_ADD
    assert 0 == len(target.delete), ZERO_DEL


def test_mismatched_acl_fields():
    acls = create_write_acls(MAC, ACLPermissionType.DENY)
    status = RdfmDeviceWriteAuthorizationStatus.init_from_acls(acls)
    topic_name = device_mac_to_topic_name(MAC)

    # principal name mismatch
    wrong = ACL(principal=f"User:WRONG:PRINCIPAL",
                host="*",
                operation=ACLOperation.WRITE,
                permission_type=ACLPermissionType.ALLOW,
                resource_pattern=ResourcePattern(ResourceType.TOPIC, topic_name))
    with pytest.raises(ValueError):
        status.init_from_acls(acls + [wrong])

    # resource type mismatch
    wrong = ACL(principal=f"User:{MAC}",
                host="*",
                operation=ACLOperation.WRITE,
                permission_type=ACLPermissionType.ALLOW,
                resource_pattern=ResourcePattern(ResourceType.GROUP, topic_name))  # type GROUP
    with pytest.raises(ValueError):
        status.init_from_acls(acls + [wrong])

    # resource pattern type mismatch
    wrong = ACL(principal=f"User:{MAC}",
                host="*",
                operation=ACLOperation.WRITE,
                permission_type=ACLPermissionType.ALLOW,
                resource_pattern=ResourcePattern(ResourceType.TOPIC,
                                                 topic_name,
                                                 pattern_type=ACLResourcePatternType.PREFIXED))  # pattern type
    with pytest.raises(ValueError):
        status.init_from_acls(acls + [wrong])

    # topic name mismatch
    wrong = ACL(principal=f"User:{MAC}",
                host="*",
                operation=ACLOperation.WRITE,
                permission_type=ACLPermissionType.ALLOW,
                resource_pattern=ResourcePattern(ResourceType.TOPIC, "WRONG-TOPIC"))
    with pytest.raises(ValueError):
        status.init_from_acls(acls + [wrong])


# ACL alteration response handling
# The below errors are fictional scenarios and may not resemble
# the actual ways in which an addition/deletion operation fails.


def test_handle_successful_creation_result():
    result = { "succeeded": [], "failed": [] }
    assert handle_acl_creation_result(result) is None, "Result with no failures should be regarded as successful"


def test_handle_unsucessful_creation_result():
    failed = [(acl, Errors.UnknownTopicOrPartitionError)
              for acl in create_write_acls(MAC, ACLPermissionType.ALLOW)]
    result = {
            "succeeded": [],
            "failed": failed
            }
    err = handle_acl_creation_result(result)
    assert type(err) is ExceptionGroup, "Failures should be put in ExceptionGroup and returned"
    assert len(failed) == len(err.exceptions), ("Number of exceptions in ExceptionGroup"
                                                " should match the number of declared failures")


def test_handle_successful_deletion_result():
    filter, acls = create_filter_and_acls(MAC, ACLPermissionType.DENY)
    result = [
            (filter,
             [(acl, Errors.NoError)
              for acl in acls],
             Errors.NoError)
            ]
    assert handle_acl_deletion_result(result) is None, "Result with no failures should be regarded as successful"


def test_handle_unsuccessful_deletion_result():
    filter, acls = create_filter_and_acls(MAC, ACLPermissionType.DENY)
    result = [
            (filter,
             [(acl, Errors.UnknownTopicOrPartitionError)
              for acl in acls],
             Exception)
            ]
    err = handle_acl_deletion_result(result)
    assert type(err) is ExceptionGroup, "Failures should be put in ExceptionGroup and returned"
    assert 2 == len(err.exceptions), ("There should be one top level filter failure"
                                      " and one nested ExceptionGroup with the partial failures")
    assert type(err.exceptions[-1]) is ExceptionGroup, "The nested failure should be of type ExceptionGroup"
    assert len(acls) == len(err.exceptions[-1].exceptions), "The nested failures should match the number of created failed ACLs"


def test_handle_unsuccessful_deletion_result_filter():
    filter, acls = create_filter_and_acls(MAC, ACLPermissionType.DENY)
    result = [
            (filter,
             [(acl, Errors.NoError)
              for acl in acls],
             Exception
              )
            ]  # Places error only on the filter level
    err = handle_acl_deletion_result(result)
    assert type(err) is ExceptionGroup, "Failures should be put in ExceptionGroup and returned"
    assert 1 == len(err.exceptions), ("There should only be 1 exception stored in the group"
                                      " since there's only a filter level failure")


def test_handle_unsuccessful_deletion_result_partial():
    filter, acls = create_filter_and_acls(MAC, ACLPermissionType.DENY)
    result = [
            (filter,
             [(acl, Errors.UnknownTopicOrPartitionError)
              for acl in acls],
             Errors.NoError
              )
            ]  # Places errors only on the partial acl level
    err = handle_acl_deletion_result(result)
    assert type(err) is ExceptionGroup, "Failures should be put in ExceptionGroup and returned"
    assert 1 == len(err.exceptions), ("There should only be 1 exception stored in the group"
                                      " which is a nested group of partial failures")
    assert type(err.exceptions[0]) is ExceptionGroup, "The nested group should be of type ExceptionGroup"
    assert len(acls) == len(err.exceptions[0].exceptions), "The nested failures should match the number of created failed ACLs"
