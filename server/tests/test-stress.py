import asyncio
import pytest
import os
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import Awaitable
from mocks.device import MockedDevice
from scripts.parse_stress_logs import parse
from common import (
    auth_pending,
    group_assign_devices,
    group_assign_packages,
    group_change_policy,
    group_create,
    package_create_dummy,
    package_fetch_all,
)

DEV_VER = "dummy"
PARENT_DIR = Path(__file__).parent
DEV_DIR = PARENT_DIR / "devices"
LOGS_DIR = PARENT_DIR / "logs"


def create_mac_addr(n: int) -> str:
    """Creates MAC address based on received `n`."""
    return ":".join([f"{n:012d}"[i : i + 2] for i in range(0, 12, 2)])


def create_devices(
    n: int,
    version: str,
    devtype: str,
    starts_from: int = 0,
) -> list:
    """Creates `n` devices with specified `version` and `devtype`."""
    devs = []
    for i in range(starts_from, starts_from + n):
        devs.append(MockedDevice(create_mac_addr(i), version, devtype))
        devs[-1].save(DEV_DIR)
    return devs


async def create_subprocess(
    devs: list[MockedDevice], *args, file=None
) -> Awaitable[list[int]]:
    """Creates one subproces for each device,
        running `loop` function from MockedDevice.

    Args:
        devs: List of devices
        args: Arguments for the subprocess command
        file: File where subprocess output will be saved

    Returns:
        Awaitable object with all created subprocesses
    """
    print("Creating processes...")
    tasks = await asyncio.gather(
        *[
            asyncio.create_subprocess_exec(
                sys.executable,
                "mocks/device.py",
                *args,
                str(DEV_DIR / f"{dev.mac_addr}.pickle"),
                stdout=file,
                cwd=PARENT_DIR,
                env={
                    "PYTHONPATH": str(PARENT_DIR.resolve()),
                    **os.environ,
                },
            )
            for dev in devs
        ]
    )
    print("Processes created")
    # Tasks waiting for all subprocesses
    return asyncio.gather(*[task.wait() for task in tasks])


def _time(func):
    """Decorator wrapping `func` with time measuring mechanism."""

    def decorated_func(*args, **kwargs):
        dt = datetime.utcnow()
        result = func(*args, **kwargs)
        dtn = datetime.utcnow()
        return (dtn - dt).total_seconds(), result

    return decorated_func


async def _run(n: int, package_size: float = 5.0):
    """The main scenario creating devices, registering them,
        uploading package, creating group and assigning update.

    Args:
        n: Number of devices to create
        package_size: Size of the created package in MB
    """
    LOGS_DIR.mkdir(exist_ok=True)
    DEV_DIR.mkdir(exist_ok=True)
    devs = create_devices(n, "v0.0.1", DEV_VER)

    logs_auth = (LOGS_DIR / f"auth{n}.log").open("w")
    result_auth = await create_subprocess(
        devs,
        "--methods",
        "auth",
        "--save",
        file=logs_auth,
    )
    await asyncio.sleep(10.0)

    while len(auth_pending()) != n:
        print("Waiting for all devices to be pending")
        await asyncio.sleep(2.0)
    # Register all devices
    async with httpx.AsyncClient(timeout=None) as session:
        responses = await asyncio.gather(*[dev.register(session) for dev in devs])
        while unapproved := [
            dev for dev, response in zip(devs, responses) if response.status_code != 200
        ]:
            print(f"{len(responses)} devices still needs to be registered")
            responses = await asyncio.gather(
                *[dev.register(session) for dev in unapproved]
            )
    print("All devices registered")
    # Wait for all subprocesses to end
    assert all([r == 0 for r in await result_auth])
    logs_auth.close()
    print("All tokens received")

    logs_update = (LOGS_DIR / f"update{n}.log").open("w")
    result_update = await create_subprocess(
        devs,
        "--methods",
        "check_update",
        "--save",
        file=logs_update,
    )
    await asyncio.sleep(5.0)

    t, group = _time(group_create)()
    print("Creating group:", t)

    version = "v0.0.2"
    t, _ = _time(package_create_dummy)(
        {
            "rdfm.software.version": version,
            "rdfm.hardware.devtype": DEV_VER,
        },
        int(1024 * 1024 * package_size),
    )
    print("Uploading package:", t)
    t, package = _time(package_fetch_all)()
    package = package[-1]
    print("Fetching packages:", t)

    # Reload mocked devices with ID
    devs = [MockedDevice.load(DEV_DIR / f"{dev.mac_addr}.pickle") for dev in devs]
    t, _ = _time(group_assign_devices)(group["id"], [dev.id for dev in devs])
    print("Device assigned:", t)
    t, _ = _time(group_assign_packages)(group["id"], [package["id"]])
    print("Package assigned:", t)
    await asyncio.sleep(5.0)
    t, _ = _time(group_change_policy)(group["id"], f"exact_match,{version}")
    print("Policy set:", t)

    # Wait for all subprocesses to end
    result_update = await result_update
    assert all([r == 0 for r in result_update])
    logs_update.close()

    devs = [MockedDevice.load(DEV_DIR / f"{dev.mac_addr}.pickle") for dev in devs]
    assert all(dev.ver == version for dev in devs)
    stats = parse([LOGS_DIR / f"auth{n}.log", LOGS_DIR / f"update{n}.log"])
    with open(str(LOGS_DIR / f"metrics{n}.json"), "w") as fd:
        json.dump(stats, fd)


@pytest.mark.parametrize(
    "n",
    [
        pytest.param(n, marks=[pytest.mark.asyncio])
        for n in (5, 50, 150, 300, 600, 1000)
    ],
)
async def test_stress(process_gunicorn, n):
    await _run(n, package_size=50)
