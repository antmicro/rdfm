import pytest
from storage.common import upload_part_count
import requests
import pytest
from mocks.device import MockedDevice
import httpx
import simple_websocket
import threading
import time
import json
import random


SERVER = "http://127.0.0.1:5000/"

def download_endpoint(device_id):
    return f"/api/v2/devices/{device_id}/fs/file"


FILES = {
    "/data/file1": b"\00\01\02\03",
    "/data/file2": b"\00\01\02\03" * 10 * 2**20,
    "/data/file3": random.randbytes(50 * 2**20)
}

def client_ws(dev):
    ws = simple_websocket.Client.connect(f"{SERVER}/api/v1/devices/ws", headers={"Authorization": f"Bearer token={dev.token}"})
    ws.send(json.dumps({
        "method": "capability_report",
        "capabilities": {
            "filesystem": True,
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
            case "fs_file_probe":
                resp = {
                    "method": "fs_file_probe_reply",
                    "id": data["id"],
                    "status": 1,
                    "size": 0
                }
                if data["file"] in FILES:
                    resp["status"] = 0
                    resp["size"] = len(FILES[data["file"]])

                ws.send(json.dumps(resp))
            case "fs_file_download":
                resp = {
                    "method": "fs_file_download_reply",
                    "id": data["id"],
                    "status": 1,
                    "etags": []
                }
                if data["file"] in FILES:
                    part_size = int(data["part_size"])
                    file_len = len(FILES[data["file"]])
                    start = 0
                    for url in data["upload_urls"]:
                        size = min(part_size, file_len - start)
                        put_resp = requests.put(url, data=FILES[data["file"]][start:start+size])
                        resp["etags"].append(put_resp.headers["Etag"])
                        start += part_size
                    resp["status"] = 0
                ws.send(json.dumps(resp))
            case _:
                ws.send(json.dumps({}))


async def client(dev):
    dev.auth()
    async with httpx.AsyncClient(timeout=None) as session:
        await dev.register(session)
    dev.auth()

    t = threading.Thread(target=client_ws, args=(dev,))
    t.start()


@pytest.mark.asyncio
async def test_file_download(process):
    dev = MockedDevice("00:00:00:00:00:00", "v0", "dummy")
    await client(dev)

    time.sleep(1) # otherwise the first request might be sent too fast

    for file, content in FILES.items():
        resp = requests.get(
            f"{SERVER}/{download_endpoint(1)}",
            headers={
                "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            },
            json={"file": file}
        )

        assert resp.status_code == 200
        resp = resp.json()
        assert resp["status"] == 0

        file = requests.get(resp["url"], stream=True)
        assert file.status_code == 200
        assert len(file.content) == len(content)
        assert file.content == content


def test_non_existing_device_download(process):
    resp = requests.get(
        f"{SERVER}/{download_endpoint(0)}",
        headers={
            "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        },
        json={"file": "some-file"}
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_non_existing_file_download(process):
    dev = MockedDevice("00:00:00:00:00:00", "v0", "dummy")
    await client(dev)

    time.sleep(1) # otherwise the first request might be sent too fast

    resp = requests.get(
        f"{SERVER}/{download_endpoint(1)}",
        headers={
            "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        },
        json={"file": "this-file-does-not-exist"}
    )

    assert resp.status_code == 200
    resp = resp.json()
    assert resp["status"] == 1


def test_file_upload_part_split():
    """ Test if size of upload parts and their count is properly calculated and don't violate S3 contraints """
    # limits based on
    # https://docs.aws.amazon.com/en_us/AmazonS3/latest/userguide/qfacts.html
    MIN_PART_SIZE = 5 * 2**20  # last part has no minimum size limit
    MAX_PART_SIZE = 5 * 2**30
    MAX_PART_COUNT = 10000
    MAX_UPLOAD_SIZE = 5 * 2**40

    KB = 2**10
    MB = 2**20
    GB = 2**30
    TB = 2**40

    test_data = [
        (1 * KB, 10 * MB),
        (5 * MB, 10 * MB),
        (12 * MB, 10 * MB),
        (16 * MB, 100 * MB),
        (200 * MB, 10 * MB),
        (2 * GB, 10 * MB),
        (2 * GB, 100 * MB),
        (1 * TB, 5 * MB),
        (1 * TB, 100 * MB),
    ]

    for upload_size, desired_part_size in test_data:
        part_c, part_size = upload_part_count(upload_size, desired_part_size)
        assert part_c * part_size >= upload_size, "not enough parts/not enough part size to upload whole file"
        if part_c > 1:
            assert part_size >= MIN_PART_SIZE and part_size <= MAX_PART_SIZE, "part size contraint violated"
        assert part_c <= MAX_PART_COUNT, "too many parts"

    too_big_file = MAX_UPLOAD_SIZE * 2
    with pytest.raises(Exception) as exc_test:
        part_c, part_size = upload_part_count(too_big_file, MAX_PART_SIZE)

