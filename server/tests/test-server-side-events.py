import pytest
import time
import json
import requests
from sqlalchemy import null
from mocks.device import MockedDevice
import httpx
import simple_websocket
import threading

SERVER = "http://127.0.0.1:5000/"
STREAM_ENDPOINT = f"{SERVER}/api/stream";

def client_ws(dev):
    ws = simple_websocket.Client.connect(f"{SERVER}/api/v1/devices/ws", headers={"Authorization": f"Bearer token={dev.token}"})
    ws.send(json.dumps({
        "method": "capability_report",
        "capabilities": {
            "update-progress": True
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
                pass
            case _:
                ws.send(json.dumps({}))

        for i in range(1, 101):
            update = {
                "method": "update_progress",
                "progress": i,
            }
            ws.send(json.dumps(update))
            time.sleep(0.1)


async def client(dev):
    dev.auth()
    async with httpx.AsyncClient(timeout=None) as session:
        await dev.register(session)
    dev.auth()

    t = threading.Thread(target=client_ws, args=(dev,))
    t.start()


@pytest.mark.asyncio
async def test_server_side_events(process_gunicorn, redis_server):
    # Connect device
    dev = MockedDevice("00:00:00:00:00:00", "v0", "dummy")
    await client(dev)

    time.sleep(1)

    # Read updates from stream
    resp = requests.get(STREAM_ENDPOINT, stream=True)

    print(resp.__dict__)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["Content-Type"]

    for message in resp.iter_lines():
        if message:
            decoded = message.decode()
            assert decoded.startswith("event:update") or decoded.startswith("data:")

            if decoded.startswith("data:"):
                update = json.loads(decoded.removeprefix("data:"))
                assert update["device"] == "00:00:00:00:00:00"
                assert update["version"] == None
                assert update["progress"] > 0 and update["progress"] < 101

                if update["progress"] == 100:
                    break

