import pytest
import time
import json
import requests
from sqlalchemy import null
from mocks.device import MockedDevice
import httpx
import simple_websocket
import threading
from typing import Generator
from common import *

PROGRESS_ALL_ENDPOINT = f"{SERVER}/api/v2/devices/progress"
PROGRESS_ONE_ENDPOINT_TEMPLATE = f"{SERVER}/api/v2/devices/{{device_id}}/progress"


def client_ws(dev: MockedDevice) -> Generator:
    ws = simple_websocket.Client.connect(
        f"{SERVER}/api/v1/devices/ws",
        headers={"Authorization": f"Bearer token={dev.token}"})
    ws.send(
        json.dumps({
            "method": "capability_report",
            "capabilities": {
                "update-progress": True
            }
        }))

    try:
        data = ws.receive()
    except:
        return
    data = json.loads(data)
    match data["method"]:
        case "alert":
            pass
        case _:
            ws.send(json.dumps({}))

    update = {
        "method": "update_progress",
        "progress": 0,
    }
    for i in range(1, 101):
        update["progress"] = i
        ws.send(json.dumps(update))
        time.sleep(0.1)
        yield i


async def client(dev: MockedDevice) -> None:
    dev.auth()
    async with httpx.AsyncClient(timeout=None) as session:
        await dev.register(session)
    dev.auth()


def setup_dummy_update(device_id: int) -> None:
    resp = package_create_dummy({
        "rdfm.software.version": "v1",
        "rdfm.hardware.devtype": "",
    })
    pkg_id = resp.json().get("id")
    resp = group_create()
    gid = resp.get("id")
    group_assign_packages(gid, [pkg_id])
    group_assign_devices(gid, [device_id])
    group_change_policy(gid, "exact_match,v1")


def ensure_progress_empty(device_id: int) -> None:
    resp = requests.get(PROGRESS_ALL_ENDPOINT)
    assert resp.status_code == 200, "Failed to fetch list of updates in progress"
    assert resp.json(
    ) == [], "Unexpected response for updates in progress query (expected empty list)"

    PROGRESS_ONE_ENDPOINT = PROGRESS_ONE_ENDPOINT_TEMPLATE.format(
        device_id=device_id)
    resp = requests.get(PROGRESS_ONE_ENDPOINT)
    assert resp.status_code == 204, "Unexpected response to update status for device (expected empty response)"


@pytest.mark.asyncio
async def test_progress_api(process_gunicorn) -> None:
    # Connect device
    dev = MockedDevice("00:00:00:00:00:00", "v0", "dummy")
    await client(dev)
    assert dev.id is not None, "Error registering mock device"
    # Create group and dummy package
    setup_dummy_update(dev.id)

    # Verify behavior with no update in progress
    ensure_progress_empty(dev.id)

    # Check for updates
    pkg_id = update_check({
        "rdfm.software.version": "",
        "rdfm.hardware.macaddr": dev.mac_addr,
        "rdfm.hardware.devtype": ""
    })
    assert pkg_id is not None, "Failed to find newly available update package"

    PROGRESS_ONE_ENDPOINT = PROGRESS_ONE_ENDPOINT_TEMPLATE.format(
        device_id=dev.id)

    for progress in client_ws(dev):
        if progress >= 100:
            break
        for endpt in (PROGRESS_ALL_ENDPOINT, PROGRESS_ONE_ENDPOINT):
            resp = requests.get(endpt)
            assert resp.status_code == 200, f"Failed to query updates in progress on {endpt}"
            updates = resp.json()
            if endpt == PROGRESS_ALL_ENDPOINT:
                assert isinstance(
                    updates,
                    list), "Unexpected response for updates in progress query"
                update = next(
                    (item for item in updates if item.get("id") == dev.id),
                    None)
            elif endpt == PROGRESS_ONE_ENDPOINT:
                update = updates
            assert isinstance(
                update,
                dict), f"Failed to fetch update status for device on {endpt}"
            assert update.get(
                "mac_address"
            ) == dev.mac_addr, "Device with matching ID has different MAC address"
            assert update.get(
                "progress"
            ) == progress, "Server failed to acknowledge progress"

    ensure_progress_empty(dev.id)
