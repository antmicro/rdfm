from __future__ import annotations

import os
import sys
import json
import argparse
import requests
from base64 import b64encode
from copy import copy
from time import sleep
from pathlib import Path
from hashlib import sha256
from pickle import dump, load
from datetime import datetime
from tempfile import TemporaryDirectory
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
    load_pem_private_key,
)

from common import (
    package_fetch_all,
    device_fetch_all,
    AUTH_ENDPOINT,
    UPDATES_ENDPOINT,
)


def generate_ssh_key_pair():
    """Generates SSH key pair.

    Returns:
        Pair of private key object and public key as string
    """
    key = generate_private_key(
        backend=default_backend(),
        public_exponent=65537,
        key_size=2048,
    )
    return (
        key,
        key.public_key()
        .public_bytes(
            Encoding.PEM,
            PublicFormat.SubjectPublicKeyInfo,
        )
        .decode(),
    )


class MockedDevice:
    def __init__(self, mac_addr, ver, devtype):
        self.mac_addr = mac_addr
        self.ver = ver
        self.devtype = devtype
        self.key, self.public_key = generate_ssh_key_pair()
        self.token = None
        self.id = None

    def _send(self, url: str, data: dict, key, token=None):
        """Sends `data` to `url` and measures response time."""
        sign = key.sign(json.dumps(data).encode(), PKCS1v15(), SHA256())
        auth_header = (
            {
                "Authorization": f"Bearer token={token}",
            }
            if token
            else {}
        )
        dt = datetime.utcnow()
        response = requests.post(
            url,
            json=data,
            headers={
                "X-RDFM-Device-Signature": b64encode(sign),
                **auth_header,
            },
        )
        dtn = datetime.utcnow()
        print(
            dtn.isoformat(),
            self.mac_addr,
            url,
            response.status_code,
            (dtn - dt).total_seconds(),
        )
        if response.status_code == 200:
            return response
        elif response.status_code == 204:
            return False
        return None

    def send_with_reauthorization(
        self,
        url: str,
        data: dict,
        token: str = None,
        retry: bool = False,
    ):
        """Sends message and optionally tires to re-autohrize the device
            if token expired.

        Args:
            url: Address where message will be send
            data: Content of the message
            token: Authorization token
            retry: Enable re-authorization
        """
        resp = self._send(url, data, self.key, token)
        if resp is None and retry:
            self.auth()
            resp = self._send(url, data, self.key, self.token)
        return resp if resp else None

    def auth(self) -> bool:
        """Sends authorization request.

        Returns:
            True, if authorized
            False, otherwise
        """
        response = self.send_with_reauthorization(
            f"{AUTH_ENDPOINT}/device",
            {
                "metadata": {
                    "rdfm.software.version": self.ver,
                    "rdfm.hardware.devtype": "dummy",
                    "rdfm.hardware.macaddr": self.mac_addr,
                },
                "public_key": self.public_key,
                "timestamp": int(datetime.utcnow().timestamp()),
            },
        )
        if response:
            self.token = response.json()["token"]
            self.id = [
                d for d in device_fetch_all() if d["mac_address"] == self.mac_addr
            ][0]["id"]
            return True
        return False

    def register(self, session):
        """Creates asyncronus registration request."""
        return session.post(
            f"{AUTH_ENDPOINT}/register",
            json={
                "mac_address": self.mac_addr,
                "public_key": self.public_key,
            },
        )

    def check_update(self) -> bool:
        """Checks if there is update available,
        downloads it and bumps version.
        """
        update = self.send_with_reauthorization(
            UPDATES_ENDPOINT,
            {
                "rdfm.software.version": self.ver,
                "rdfm.hardware.devtype": "dummy",
                "rdfm.hardware.macaddr": self.mac_addr,
            },
            token=self.token,
            retry=True,
        )
        if update:
            update = update.json()
            return self.download_package(update["uri"], update["sha256"], update["id"])
        return False

    def download_package(self, package_url, package_sha, package_id) -> bool:
        """Downloads package `package_id` from `package_url`,
        checks if hash equals `package_sha` and updates device's version.
        """
        with TemporaryDirectory() as tmp:
            dt = datetime.utcnow()
            os.system(f"cd {tmp} && wget {package_url} > /dev/null 2> /dev/null")
            dtn = datetime.utcnow()
            files = list(Path(tmp).glob("*"))
            with open(files[0], "rb") as package:
                sha = sha256(package.read())
        if package_sha == sha.hexdigest():
            self.ver = [p for p in package_fetch_all() if package_id == p["id"]][0][
                "metadata"
            ]["rdfm.software.version"]
            print(
                dtn.isoformat(),
                self.mac_addr,
                package_url,
                200,
                (dtn - dt).total_seconds(),
            )
            return True
        print(
            dtn.isoformat(), self.mac_addr, package_url, 401, (dtn - dt).total_seconds()
        )
        return False

    def save(self, dir: Path):
        """Saves device to pickle file in directory `dir`."""
        dir.mkdir(exist_ok=True)
        s = copy(self)
        s.key = self.key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,
            NoEncryption(),
        )
        with open(dir / f"{self.mac_addr}.pickle", "wb") as fd:
            dump(s, fd)

    @classmethod
    def load(cls, file: Path) -> MockedDevice:
        """Loads device from `file`."""
        with open(file, "rb") as fd:
            s = load(fd)
        s.key = load_pem_private_key(s.key, None, default_backend())
        return s


def loop(
    dev_file: Path,
    methods: list[str] = None,
    repeat: int = None,
    period: float = 1.0,
    save: bool = False,
):
    """Loads device, and run its method predefined number of times.

    Args:
        dev_file: Pickle file with saved MockedDevice
        methods: List with MockedDevice methods that should be called
        repeat: How many times call should be repeated,
            if None repeats until returned value is True
        period: Time between consequitive method calls
        save: Should device be saved after successful method call
    """
    assert repeat is None or repeat > 0
    dev = MockedDevice.load(dev_file)
    for method in methods:
        dev_method = getattr(dev, method)
        if repeat is not None:
            for r in range(repeat):
                sleep(period)
                dev_method()
        else:
            while not dev_method():
                sleep(period)
        if save:
            dev.save(dev_file.parent)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dev_file", type=Path, help="Path to the pickle file with MockedDevice"
    )
    parser.add_argument(
        "--methods", type=str, action="append", help="List of methods to run"
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=None,
        help="How many times method should be repeated",
    )
    parser.add_argument(
        "--period", type=float, default=1.0, help="Time between calls of the method"
    )
    parser.add_argument("--save", action="store_true")

    args = parser.parse_args(sys.argv[1:])
    loop(args.dev_file, args.methods, args.repeat, args.period, args.save)
