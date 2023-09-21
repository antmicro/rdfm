import pexpect
import time
import os
import json
import sys
import requests
import subprocess


SERVER = "http://127.0.0.1:5000/"
PACKAGES_ENDPOINT = f"{SERVER}/api/v1/packages"
TESTING_PACKAGE_SIZE = 1024

process = subprocess.Popen(["python3", "-m", "rdfm_mgmt_server", "--debug", "--no-ssl"])
time.sleep(5)

try:
    # Check if package endpoint returns data
    packages = requests.get(PACKAGES_ENDPOINT)
    assert packages.status_code == 200
    assert packages.content == b"[]\n"

    # Try uploading a package
    dummy_package = {
        "rdfm.software.version": (None, "v1"),
        "rdfm.hardware.devtype": (None, "dummydevice"),
        "file": ("file", b"\xff" * TESTING_PACKAGE_SIZE)
    }
    response = requests.post(PACKAGES_ENDPOINT, files=dummy_package)
    assert response.status_code == 200

    # Now check if the endpoint returns sane data
    packages = requests.get(PACKAGES_ENDPOINT)
    assert packages.status_code == 200
    response = packages.json()
    assert len(response) > 0
    assert response[0]["metadata"]["rdfm.software.version"] == "v1"
    assert response[0]["metadata"]["rdfm.hardware.devtype"] == "dummydevice"

    # Check if single package fetch endpoint works
    pkgid = response[0]["id"]
    response_single = requests.get(f"{PACKAGES_ENDPOINT}/{pkgid}")
    assert response_single.status_code == 200

    # Now delete the package
    delete = requests.delete(f"{PACKAGES_ENDPOINT}/{pkgid}")
    assert delete.status_code == 200

    # The package should now 404
    response_single = requests.get(f"{PACKAGES_ENDPOINT}/{pkgid}")
    assert response_single.status_code == 404

    print("\033[0;32m", "Package tests passed!", "\033[0m")
finally:
    process.kill()
