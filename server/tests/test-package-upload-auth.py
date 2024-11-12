import requests
import pytest
import os
import subprocess
import time
from typing import Optional
import json
from mocks.oauth2_token_introspection import (start_token_mock,
                                              configure_token_mock,
                                              MockConfig)
import io
import tarfile
import tempfile
from api.v1.middleware import SCOPE_READ_ONLY, SCOPE_READ_WRITE, SCOPE_SINGLE_FILE, SCOPE_ROOTFS_IMAGE
from common import SERVER_WAIT_TIMEOUT, wait_for_api
from pathlib import Path

SERVER = "http://127.0.0.1:5000/"
DBPATH = "test-db.db"

""" Upload packages endpoint to use for testing different scopes
"""
TEST_UPLOAD_ENDPOINT = "/api/v1/packages"

""" Payload to send to the above endpoint when testing RW scopes """
TEST_SINGLE_FILE_DATA = {"payloads": [ { "type": "single-file" } ] }
TEST_ROOTFS_IMAGE_DATA = {"payloads": [ { "type": "rootfs-image" } ] }


@pytest.fixture
def rdfm_artifact(request):
    """ Create an artifact.rdfm file for testing
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        header_name = 'header.tar'
        header_path = tmpdirname + '/' + header_name

        with tarfile.open(header_path, "x") as header_info_tar:
            # Creating a header-info file with the payload
            info = tarfile.TarInfo("header-info")

            info.size = len(json.dumps(request.param).encode('utf-8'))
            header_info_tar.addfile(info, fileobj=io.BytesIO(json.dumps(request.param).encode('utf-8')))

        artifact_name = 'artifact.rdfm'
        artifact_path = tmpdirname + '/' + artifact_name

        with tarfile.open(artifact_path, "x") as header_tar:
            # Creating a artifact.rdfm tar containing the header.tar file
            header_tar.add(header_path, 'header.tar')

        yield artifact_path


@pytest.fixture()
def process(db, configure_token_mock, request):
    new_env = os.environ.copy()
    new_env["JWT_SECRET"] = "TESTDEVELOPMENTSECRET123"
    new_env["RDFM_OAUTH_URL"] = configure_token_mock
    new_env["RDFM_LOGIN_URL"] = "http://test.url"
    new_env["RDFM_LOGOUT_URL"] = "http://test.url"
    new_env["RDFM_OAUTH_CLIENT_ID"] = "rdfm-server-introspection"
    new_env["RDFM_OAUTH_CLIENT_SEC"] = "qPsZzvAUtDVREjJyuyAEu3SDBQElATgX"

    print("Starting server..")

    process = subprocess.Popen(
        [
            "poetry", "run", "python3", "-m", "rdfm_mgmt_server",
            "--debug", "--no-ssl", "--test-mocks", "--database", request.getfixturevalue(db)
        ],
        env=new_env,
    )
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER, success_status=401), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()


def _scope_error(endpoint_type: str,
                 scope_type: str,
                 result: str):
    """ Helper for formatting scope test error messages
    """
    return f"accessing a {endpoint_type} endpoint using a token with {scope_type} scope(s) should be {result}"


SCOPES_UPLOAD_TEST_DATA = [
    (MockConfig(valid=True, scopes=[SCOPE_READ_WRITE], user_id="test-user-id"), 200, _scope_error("upload-single-file, read-write", "read-write", "accepted"), TEST_SINGLE_FILE_DATA),
    (MockConfig(valid=True, scopes=[SCOPE_SINGLE_FILE], user_id="test-user-id"), 200, _scope_error("upload-single-file, read-write", "upload-single-file", "accepted"), TEST_SINGLE_FILE_DATA),
    (MockConfig(valid=True, scopes=[SCOPE_READ_ONLY], user_id="test-user-id"), 403, _scope_error("upload-single-file, read-write", "read-only", "rejected"), TEST_SINGLE_FILE_DATA),
    (MockConfig(valid=True, scopes=[SCOPE_ROOTFS_IMAGE], user_id="test-user-id"), 403, _scope_error("upload-single-file, read-write", "upload-rootfs-image", "rejected"), TEST_SINGLE_FILE_DATA),
    (MockConfig(valid=True, scopes=[SCOPE_READ_WRITE], user_id="test-user-id"), 200, _scope_error("upload-rootfs-image, read-write", "read-write", "accepted"), TEST_ROOTFS_IMAGE_DATA),
    (MockConfig(valid=True, scopes=[SCOPE_ROOTFS_IMAGE], user_id="test-user-id"), 200, _scope_error("upload-rootfs-image, read-write", "upload-rootfs-image", "accepted"), TEST_ROOTFS_IMAGE_DATA),
    (MockConfig(valid=True, scopes=[SCOPE_SINGLE_FILE], user_id="test-user-id"), 403, _scope_error("upload-rootfs-image, read-write", "upload-single-file", "rejected"), TEST_ROOTFS_IMAGE_DATA),
    (MockConfig(valid=True, scopes=[SCOPE_READ_ONLY], user_id="test-user-id"), 403, _scope_error("upload-rootfs-image, read-write", "read-only", "rejected"), TEST_ROOTFS_IMAGE_DATA),
    (MockConfig(valid=True, scopes=[], user_id="test-user-id"), 403, _scope_error("upload-single-file, read-write", "none", "rejected"), TEST_SINGLE_FILE_DATA),
]

@pytest.mark.parametrize('token_mock_config,expected_status,error_message,rdfm_artifact, ', SCOPES_UPLOAD_TEST_DATA, indirect=["rdfm_artifact"])
def test_upload_artifact(process,
                                                  expected_status: int,
                                                  error_message: str,
                                                  rdfm_artifact: str,):
    """ This tests uploading a single-file and a rootfs-image artifacts using different tokens.

    For each token, a POST request is made to the predefined endpoint with a
    generic payload and the response is checked against an expected value.
    """
    with open(rdfm_artifact, "rb") as f:
        resp = requests.post(
            f"{SERVER}/{TEST_UPLOAD_ENDPOINT}",
            headers={
                "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            },
            data={
                    "rdfm.software.version": "1.0.0",
                    "rdfm.software.devtype": "dummy",
            },
            files={"file": f},
        )
    assert resp.status_code == expected_status, error_message
