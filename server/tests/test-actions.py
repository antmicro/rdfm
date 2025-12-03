import pytest
import time
import json
import requests
from mocks.device import MockedDevice
import httpx
import simple_websocket
import threading

SERVER = "http://127.0.0.1:5000/"
DEVICE_ACTIONS_ENDPOINT = f"{SERVER}/api/v2/devices/00:00:00:00:00:00/action/list"
DEVICE_ACTIONS_VALID_EXEC_ENDPOINT = f"{SERVER}/api/v2/devices/00:00:00:00:00:00/action/exec/valid"
DEVICE_ACTIONS_INVALID_EXEC_ENDPOINT = f"{SERVER}/api/v2/devices/00:00:00:00:00:00/action/exec/invalid"
DEVICE_ACTION_LOG_ENDPOINT = f"{SERVER}/api/v2/devices/00:00:00:00:00:00/action/log"
DEVICE_PENDING_ACTIONS_ENDPOINT = f"{SERVER}/api/v2/devices/00:00:00:00:00:00/action/pending"
DEVICE_REMOVE_ACTIONS_ENDPOINT = f"{SERVER}/api/v2/devices/00:00:00:00:00:00/action/remove"
DOWNLOAD_URL_PREFIX = f"{SERVER}local_storage_multipart/multipart/rdfm.actions"

ACTIONS = [
    {
        "action_id": "valid",
        "action_name": "Valid action",
        "description": "Description of echo action",
        "command": ["echo", "Executing echo action"],
        "timeout": 1.0
    },
    {
        "action_id": "invalid",
        "action_name": "Invalid action",
        "description": "This action will fail",
        "command": ["echo", "Executing echo action"],
        "timeout": 1.0
    }
]
DEVICE_CONNECTED = threading.Event()

def client_ws(dev, DEVICE_CONNECTED):
    ws = simple_websocket.Client.connect(f"{SERVER}/api/v1/devices/ws", headers={"Authorization": f"Bearer token={dev.token}"})
    ws.send(json.dumps({
        "method": "capability_report",
        "capabilities": {
            "action": True
        }
    }))

    while True:
        try:
            data = ws.receive()
        except:
            return
        data = json.loads(data)
        match data["method"]:
            case "alert":
                DEVICE_CONNECTED.set()
            case "action_list_query":
                resp = {
                    "method": "action_list_update",
                    "actions": ACTIONS,
                }
                ws.send(json.dumps(resp))
            case "action_exec":
                control = {
                    "method": "action_exec_control",
                    "status": "ok",
                    "execution_id": data["execution_id"],
                }
                ws.send(json.dumps(control))
                result = {
                    "method": "action_exec_result",
                    "status_code": 0 if data["action_id"] == "valid" else -1,
                    "output": "echo" if data["action_id"] == "valid" else "",
                    "execution_id": data["execution_id"],
                }
                ws.send(json.dumps(result))
            case _:
                ws.send(json.dumps({}))


async def client(dev):
    dev.auth()
    async with httpx.AsyncClient(timeout=None) as session:
        await dev.register(session)
    dev.auth()

    t = threading.Thread(target=client_ws, args=(dev, DEVICE_CONNECTED, ))
    t.start()


def wait_for_device_connection():
    start = time.time()
    timeout = 5

    while time.time() - start < timeout:
        if DEVICE_CONNECTED.is_set():
            return True
    return False


@pytest.mark.asyncio
async def test_actions(process):
    # Request action before device connects
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 500

    # Check if action appears in action log
    resp = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200
    actions = resp.json()
    assert actions[0]["action"] == "valid"
    assert actions[0]["status"] == "pending"

    # Clear action log
    resp = requests.delete(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200

    # Check if action is still in the log after clearing
    resp = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200
    actions = resp.json()
    assert actions[0]["action"] == "valid"
    assert actions[0]["status"] == "pending"

    # Connect device
    dev = MockedDevice("00:00:00:00:00:00", "v0", "dummy")
    await client(dev)
    connected = wait_for_device_connection()
    assert connected == True

    # Request action list
    resp = requests.get(DEVICE_ACTIONS_ENDPOINT)
    assert resp.status_code == 200
    actions = resp.json()
    assert actions == ACTIONS

    # Execute valid action
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 200
    result = resp.json()
    assert result["output"] == "echo"
    assert result["status_code"] == 0

    # Execute invalid action
    resp = requests.get(DEVICE_ACTIONS_INVALID_EXEC_ENDPOINT)
    assert resp.status_code == 200
    result = resp.json()
    assert result["output"] == ""
    assert result["status_code"] == -1

    # Check if all actions appear in action log
    resp = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200
    actions = resp.json()
    print(actions)
    assert actions[0]["action"] == "invalid"
    assert actions[0]["status"] == "-1"
    assert actions[0]["download_url"] == None
    assert actions[1]["action"] == "valid"
    assert actions[1]["status"] == "0"
    assert actions[1]["download_url"].startswith(DOWNLOAD_URL_PREFIX)
    assert actions[2]["action"] == "valid"
    assert actions[2]["status"] == "0"
    assert actions[2]["download_url"].startswith(DOWNLOAD_URL_PREFIX)

    # Clear action log
    resp = requests.delete(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200

    # Check if action log is empty
    action_log = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert action_log.status_code == 200
    assert action_log.content == b"[]\n"


@pytest.mark.asyncio
async def test_removing_pending_actions(process):
    # Request actions
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 500
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 500
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 500

    # Check if actions appears in action log
    resp = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200
    actions = resp.json()
    assert actions[0]["action"] == "valid"
    assert actions[0]["status"] == "pending"
    assert actions[1]["action"] == "valid"
    assert actions[1]["status"] == "pending"
    assert actions[2]["action"] == "valid"
    assert actions[2]["status"] == "pending"
    assert len(actions) == 3

    # Remove pending actions
    resp = requests.delete(DEVICE_PENDING_ACTIONS_ENDPOINT)
    assert resp.status_code == 200

    # Check if action log is empty
    action_log = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert action_log.status_code == 200
    assert action_log.content == b"[]\n"


@pytest.mark.asyncio
async def test_removing_selected_actions(process):
    # Request actions
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 500
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 500
    resp = requests.get(DEVICE_ACTIONS_VALID_EXEC_ENDPOINT)
    assert resp.status_code == 500

    # Check if action appears in action log
    resp = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200
    actions = resp.json()
    assert actions[0]["action"] == "valid"
    assert actions[0]["status"] == "pending"
    assert actions[1]["action"] == "valid"
    assert actions[1]["status"] == "pending"
    assert actions[2]["action"] == "valid"
    assert actions[2]["status"] == "pending"
    assert len(actions) == 3

    id0 = actions[0]["id"]
    id1 = actions[1]["id"]
    id2 = actions[2]["id"]
    ids = {
        "actions": [id0, id2]
    }

    # Remove two actions
    resp = requests.post(DEVICE_REMOVE_ACTIONS_ENDPOINT, json=ids)
    assert resp.status_code == 200

    # Check action log content
    resp = requests.get(DEVICE_ACTION_LOG_ENDPOINT)
    assert resp.status_code == 200
    actions = resp.json()
    assert actions[0]["id"] == id1
    assert actions[0]["action"] == "valid"
    assert actions[0]["status"] == "pending"
    assert len(actions) == 1
