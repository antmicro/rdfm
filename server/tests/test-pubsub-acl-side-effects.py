import pytest
import time
import requests
import kafka.errors as Errors
from kafka.admin import (
    NewTopic,
    ACL,
    ACLOperation,
)
from common import (
    KAFKA_TOPIC,
    KAFKA_DEVICE,
    DEVICES_ENDPOINT,
    PUBSUB_ENDPOINT,
    ProcessConfig,
    create_fake_device_token,
)
from device_mgmt.pubsub_acl import device_mac_to_topic_name
from kafka.protocol.admin import (
    CreateTopicsResponse_v3,
    DeleteTopicsResponse_v3,
)


def test_admin_client_usage(create_topic, rdfm_kafka_admin):
    """
    Test various sequences of operations of assigning/revoking device's authorization
    for a topic by directly calling methods of RdfmKafkaAdminClient.
    """
    MANUAL_OP_WAIT_MS = 5000

    # Helper functions

    def describe_write_acls() -> list[ACL]:
        acls = []
        for op in (ACLOperation.WRITE, ACLOperation.IDEMPOTENT_WRITE):
            acls += rdfm_kafka_admin._describe_acls_for_device(create_topic, create_topic, operation=op)
        return acls

    def manually_clear_acls(acls: list[ACL]):
        resp = rdfm_kafka_admin.delete_acls(acls)
        assert len(resp) == len(acls), f"Passed {len(acls)} ACLFitler(s)"
        for res in resp:
            assert res[2] is Errors.NoError, "Clearing ACLs should not have failed"

    def manually_remove_topic():
        topic_name = device_mac_to_topic_name(create_topic)
        resp = rdfm_kafka_admin.delete_topics([topic_name], timeout_ms=MANUAL_OP_WAIT_MS)
        assert type(resp) is DeleteTopicsResponse_v3
        assert 1 == len(resp.topic_error_codes)
        assert create_topic == resp.topic_error_codes[0][0]
        assert Errors.for_code(resp.topic_error_codes[0][1]) is Errors.NoError

    def manually_create_topic():
        resp = rdfm_kafka_admin.create_topics([NewTopic(
            name=create_topic,
            num_partitions=1,
            replication_factor=1)],timeout_ms=MANUAL_OP_WAIT_MS)
        assert type(resp) is CreateTopicsResponse_v3
        assert len(resp.topic_errors) == 1
        assert Errors.for_code(resp.topic_errors[0][1]) is Errors.NoError

    def wait_for_correct_acls(amount: int, timeout_s: int):
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            acls = describe_write_acls()
            if len(acls) == amount:
                return acls
            time.sleep(0.1)

        pytest.fail(f"There should be {amount} write ACLs on the broker")

    # End of helper functions

    # Topic has been created by the create_topic fixture but there are 
    # no ACLs on the broker.
    status = rdfm_kafka_admin.device_topic_status(create_topic)
    assert not status.can_write(), "device should not be able to write"
    assert not status.can_idempotent_write(), "device should not be able to idempotently write"

    # We lease a topic to the device by creating ALLOW ACLs
    rdfm_kafka_admin.lease_topic_for_device(create_topic)
    status = rdfm_kafka_admin.device_topic_status(create_topic)
    assert status.can_write(), "device should be able to write"
    assert status.can_idempotent_write(), "device should be able to idempotently write"

    # We confiscate the topic by creating DENY ACLs
    rdfm_kafka_admin.confiscate_topic_from_device(create_topic)
    status = rdfm_kafka_admin.device_topic_status(create_topic)
    assert not status.can_write(), "device should not be able to write"
    assert not status.can_idempotent_write(), "device should not be able to idempotently write"

    manually_remove_topic()
    # Clear every ACL from the broker
    acls = wait_for_correct_acls(amount=4, timeout_s=10) # 2x ALLOW + 2x DENY
    manually_clear_acls(acls)
    wait_for_correct_acls(amount=0, timeout_s=10)

    status = rdfm_kafka_admin.device_topic_status(create_topic)
    assert status is None, "device_topic_status method should return None when topic doesn't exist"

    # We try leasing a non-existent topic, thus forcing a topic creation
    rdfm_kafka_admin.lease_topic_for_device(create_topic)
    status = rdfm_kafka_admin.device_topic_status(create_topic)
    assert status.can_write(), "device should be able to write"
    assert status.can_idempotent_write(), "device should be able to idempotently write"

    # Now, try removing the topic but not cleaning the associated ACLs from the broker
    manually_remove_topic()
    wait_for_correct_acls(amount=2, timeout_s=10)  # 2x ALLOW
    status = rdfm_kafka_admin.device_topic_status(create_topic)
    assert status is None, "device_topic_status method should return None when topic doesn't exist"

    # Now, try creating the topcic that already has the associated ACLs presetn on the broker
    rdfm_kafka_admin.lease_topic_for_device(create_topic)
    status = rdfm_kafka_admin.device_topic_status(create_topic)
    assert status.can_write(), "device should be able to write"
    assert status.can_idempotent_write(), "device should be able to idempotently write"
    wait_for_correct_acls(amount=2, timeout_s=10)  # 2x ALLOW


@pytest.mark.parametrize("process_config", [ProcessConfig(enable_pubsub=True)])
def test_admin_client_via_endpoint(process, broker):
    def wait_for_correct_acls(allowed_write: bool, timeout_s: int):
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            resp = requests.get(f"{PUBSUB_ENDPOINT}/device/1")
            assert 200 == resp.status_code, "Device should exist and have an associated topic"
            payload = resp.json()
            if allowed_write == payload["idempotent_write"] and allowed_write == payload["write"]:
                return
            time.sleep(0.1)

        pytest.fail(f"ACL changes should have taken effect on the broker. Device should {'' if allowed_write else 'not'} be able to write.")

    resp = requests.get(f"{DEVICES_ENDPOINT}/1")
    assert 200 == resp.status_code, "Ensure that device mock has been inserted into the database"

    resp = requests.get(f"{PUBSUB_ENDPOINT}/device/1")
    assert 204 == resp.status_code, "Device should exist but not have an associated topic"

    # The create_fake_device_token function has the mac address of the mock device hardcoded
    # 00:00:00:00:00:00 should have the id of 1 on the mgmt server
    resp = requests.post(f"{PUBSUB_ENDPOINT}/request_topic",
                        headers={"Authorization": f"Bearer token={create_fake_device_token()}"})

    assert 200 == resp.status_code, "The device should have been leased a topic"
    payload = resp.json()
    assert KAFKA_TOPIC == payload["topic"], f"Topic should have been leased for {KAFKA_DEVICE}"

    wait_for_correct_acls(allowed_write=True, timeout_s=10)

    resp = requests.delete(f"{PUBSUB_ENDPOINT}/device/1")
    assert 200 == resp.status_code, "The topic should have been confiscated from the device"

    wait_for_correct_acls(allowed_write=False, timeout_s=10)


@pytest.mark.parametrize("process_config", [ProcessConfig(enable_pubsub=True, insert_mocks=False)])
def test_admin_client_via_endpoint_no_mocks(process, broker):
    resp = requests.get(f"{DEVICES_ENDPOINT}/1")
    assert 404 == resp.status_code, "Ensure that device mock has not been inserted into the database"

    resp = requests.get(f"{PUBSUB_ENDPOINT}/device/1")
    assert 404 == resp.status_code, "Endpoint should return 404 since mock does not exist"

    resp = requests.delete(f"{PUBSUB_ENDPOINT}/device/1")
    assert 404 == resp.status_code, "Endpoint should return 404 since mock does not exist"
