import os
import time
import pytest
import requests
import subprocess
from common import (
    DEVICES_ENDPOINT,
    LOGS_ENDPOINT,
    GROUPS_ENDPOINT,
    create_fake_device_token
)


@pytest.fixture
def list_devices():
    """Returns a request containing all devices in the db
    """
    response = requests.get(DEVICES_ENDPOINT)
    assert response.status_code == 200, "devices should have been fetched successfully"
    return response


@pytest.fixture
def list_logs(list_devices):
    """Return a flat list of dictionaries representing log entries
    """
    logs = []

    for device in list_devices.json():
        response = requests.get(f"{LOGS_ENDPOINT}/device/{device['id']}")
        logs.append(response.json())
    return [
        log
        for logss in logs
        for log in logss
    ]


@pytest.fixture
def insert_correct_log_batch():
    response = requests.post(LOGS_ENDPOINT,
                             json={
                                "batch": [
                                    {
                                        "device_timestamp": "Wed, 02 Oct 2002 15:00:00 -0000", 
                                        "name": "CPU",
                                        "entry": "0.123"
                                    },
                                    {
                                        "device_timestamp": "Wed, 02 Oct 2002 15:00:00 -0000",
                                        "name": "MEM",
                                        "entry": "0.345"
                                        
                                    }
                                ] 
                             },
                             headers={
                                 "Authorization": f"Bearer token={create_fake_device_token()}"
                             })
    assert response.status_code == 200, "the log entry should have been received correctly"


@pytest.fixture
def try_insert_malformed_log_date():
    response = requests.post(LOGS_ENDPOINT,
                             json={
                                 "batch": [
                                    {
                                        "device_timestamp": "2003-03-30 22:00:00.000000", # bad date format
                                        "name": "FS",
                                        "entry": "11.1"
                                    }
                                 ]
                             },
                             headers={
                                 "Authorization": f"Bearer token={create_fake_device_token()}"
                             })
    assert response.status_code == 400, "the server should fail deserializing the log"


@pytest.fixture
def delete_logs_from_devices(list_devices):
    for device in list_devices.json():
        response = requests.delete(f"{LOGS_ENDPOINT}/device/{device['id']}")
        assert response.status_code == 200, "deletion should have returned a success status code"


@pytest.fixture
def create_empty_group():
    test_group_metadata = {
        "metadata" : {
            "description": "test"
        },
    }
    response = requests.post(GROUPS_ENDPOINT, json=test_group_metadata)
    assert response.status_code == 200, "creating a group should succeed"
    return response


@pytest.fixture
def create_group_with_every_device(create_empty_group, list_devices):
    test_group = create_empty_group.json()
    response = requests.patch(f"{GROUPS_ENDPOINT}/{test_group['id']}/devices", json={
        "add": [device["id"] for device in list_devices.json()],
        "remove": []
    })
    assert response.status_code == 200, "device assignment modification should have succeeded"
    return test_group


@pytest.fixture
def delete_logs_from_group(create_group_with_every_device, insert_correct_log_batch):
    reponse = requests.delete(f"{LOGS_ENDPOINT}/group/{create_group_with_every_device['id']}")
    assert reponse.status_code == 200, "deletion should have succeeded"


def test_no_logs(process, list_logs):
    assert not any(list_logs), "the log db should be empty"


def test_inserted_logs(process, insert_correct_log_batch, list_logs):
    assert any(list_logs), "there should be log entries in the db"


def test_delete_logs(process, insert_correct_log_batch, delete_logs_from_devices, list_logs):
    assert not any(list_logs), "the log db should be empty"


def test_find_log_by_name(process, insert_correct_log_batch, list_logs):
    assert any(list_logs), "there should be log entries in the db"

    device_id = list_logs[0]["device_id"]
    name = list_logs[0]["name"]

    response = requests.get(f"{LOGS_ENDPOINT}/device/{device_id}?name={name}")
    assert response.status_code == 200, "fetch by log name should succeed"


def test_insert_malformed_log_date(process, try_insert_malformed_log_date, list_logs):
    assert not any(list_logs), "no log should have been inserted into the db"


def test_fetch_no_device(process):
    response = requests.get(f"{LOGS_ENDPOINT}/device/123")
    assert response.status_code == 404, "server should return that the group does not exist"


def test_fetch_since_date(process, insert_correct_log_batch, list_logs):
    assert any(list_logs), "there should be log entries in the db"

    device_id = list_logs[0]["device_id"]
    payload = {"name": list_logs[0]["name"], "since": "Thu, 25 Jul 2024 10:51:39 -0000"}

    response = requests.get(f"{LOGS_ENDPOINT}/device/{device_id}", params=payload)
    assert response.status_code == 200, "the fetch with from date should have succeeded"
    assert not response.json(), "the returned list should hold no logs since no satisfy the date requirement"


def test_fetch_to_date(process, insert_correct_log_batch, list_logs):
    assert any(list_logs), "there should be log entries in the db"

    device_id = list_logs[0]["device_id"]
    payload = {"name": list_logs[0]["name"], "to": "Thu, 25 Jul 2024 10:51:39 -0000"}

    response = requests.get(f"{LOGS_ENDPOINT}/device/{device_id}", params=payload)
    assert response.status_code == 200, "the fetch with from date should have succeeded"
    assert response.json(), "the returned list should hold logs that satisfy the requirement"


def test_fetch_malfomed_date(process, insert_correct_log_batch, list_logs):
    assert any(list_logs), "there should be log entries in the db"

    device_id = list_logs[0]["device_id"]
    payload = {"name": list_logs[0]["name"], "since": "2002-10-02T08:00:00-05:00"}

    response = requests.get(f"{LOGS_ENDPOINT}/device/{device_id}", params=payload)
    assert response.status_code == 400, "fetch with malformed date should return an error"


def test_fetch_no_group(process):
    response = requests.get(f"{LOGS_ENDPOINT}/group/1")
    assert response.status_code == 404, "server should return that the group does not exist"


def test_fetch_group(process, create_group_with_every_device, insert_correct_log_batch, list_logs):
    assert any(list_logs), "there should be log entries in the db"
    response = requests.get(f"{LOGS_ENDPOINT}/group/{create_group_with_every_device['id']}")
    assert response.status_code == 200, "the group log fetch should have succeeded"
    assert any(response.json()), "the response should be populated with json logs"


def test_fetch_empty_group(process, create_empty_group, insert_correct_log_batch, list_logs):
    assert any(list_logs), "there should be log entries in the db"
    response = requests.get(f"{LOGS_ENDPOINT}/group/{create_empty_group.json()['id']}")
    assert response.status_code == 200, "the group log fetch should have succeeded"
    assert not any(response.json())


def test_fetch_after_removal_from_group(process, create_group_with_every_device, insert_correct_log_batch, list_logs):
    response = requests.patch(f"{GROUPS_ENDPOINT}/{create_group_with_every_device['id']}/devices", json={
        "add": [],
        "remove": [list_logs[0]["device_id"]]
    })
    response = requests.get(f"{LOGS_ENDPOINT}/group/{create_group_with_every_device['id']}")
    assert response.status_code == 200, "fetch should have succeeded"
    assert not any(response.json()), "the response should hold no logs" 


def test_delete_logs_group(process, delete_logs_from_group, list_logs):
    assert not any(list_logs), "the log db should be empty"
