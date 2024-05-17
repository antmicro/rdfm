import requests
import pytest
import os
import subprocess
import time
from typing import Optional
from mocks.oauth2_token_introspection import (start_token_mock,
                                              configure_token_mock,
                                              MockConfig)
from api.v1.middleware import SCOPE_READ_ONLY, SCOPE_READ_WRITE
from common import SERVER_WAIT_TIMEOUT, wait_for_api


SERVER = "http://127.0.0.1:5000/"
DBPATH = "test-db.db"

""" Read-only endpoint to use for testing RO scopes """
TEST_RO_ENDPOINT = "/api/v1/groups"

""" Read-write endpoint to use for testing RW scopes.
    This must be an endpoint that support POST requests.
"""
TEST_RW_ENDPOINT = "/api/v1/groups"

""" Payload to send to the above endpoint when testing RW scopes """
TEST_RW_DATA = { "metadata": { "testing": 123 }}


@pytest.fixture()
def process(configure_token_mock):
    if os.path.isfile(DBPATH):
        os.remove(DBPATH)

    new_env = os.environ.copy()
    new_env["JWT_SECRET"] = "TESTDEVELOPMENTSECRET123"
    new_env["RDFM_OAUTH_URL"] = configure_token_mock
    new_env["RDFM_OAUTH_CLIENT_ID"] = "rdfm-server-introspection"
    new_env["RDFM_OAUTH_CLIENT_SEC"] = "qPsZzvAUtDVREjJyuyAEu3SDBQElATgX"

    print("Starting server..")
    process = subprocess.Popen([
        "python3", "-m", "rdfm_mgmt_server",
        "--debug", "--no-ssl", "--test-mocks", "--database", f"sqlite:///{DBPATH}"
    ], env=new_env)
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER, success_status=401), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()


@pytest.mark.parametrize('token_mock_config', [MockConfig(valid=False)])
def test_management_no_authorization_header(process):
    """ This tests whether a request with no Authorization header is properly
        rejected by the server.
    """
    resp = requests.get(f"{SERVER}/{TEST_RO_ENDPOINT}")
    assert resp.status_code == 401, "the server should reject requests without any authorization"


@pytest.mark.parametrize('token_mock_config', [MockConfig(valid=False)])
def test_management_invalid_authorization_header(process):
    """ This tests whether a request with an invalid authorization header is rejected.
    """
    resp = requests.get(f"{SERVER}/{TEST_RO_ENDPOINT}", headers={
        "Authorization": "Bearer XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    })
    assert resp.status_code == 401, "the server should reject requests with an invalid auth header"


def _scope_error(endpoint_type: str,
                 scope_type: str,
                 result: str):
    """ Helper for formatting scope test error messages
    """
    return f"accessing a {endpoint_type} endpoint using a token with {scope_type} scope(s) should be {result}"


SCOPE_RO_ACCESS_TEST_DATA = [
    (MockConfig(valid=False, scopes=[]), 401, "accessing a read-only endpoint with an invalid token should be rejected"),
    (MockConfig(valid=False, scopes=[SCOPE_READ_ONLY]), 401, "accessing a read-only endpoint with an invalid token should be rejected"),
    (MockConfig(valid=False, scopes=[SCOPE_READ_WRITE]), 401, "accessing a read-only endpoint with an invalid token should be rejected"),
    (MockConfig(valid=True, scopes=[]), 403, _scope_error("read-only", "no", "rejected")),
    (MockConfig(valid=True, scopes=[SCOPE_READ_ONLY]), 200, _scope_error("read-only", "read-only", "accepted")),
    (MockConfig(valid=True, scopes=[SCOPE_READ_WRITE]), 200, _scope_error("read-only", "read-write", "accepted")),
]
SCOPE_RW_ACCESS_TEST_DATA = [
    (MockConfig(valid=False, scopes=[]), 401, "accessing a read-write endpoint with an invalid token should be rejected"),
    (MockConfig(valid=False, scopes=[SCOPE_READ_ONLY]), 401, "accessing a read-write endpoint with an invalid token should be rejected"),
    (MockConfig(valid=False, scopes=[SCOPE_READ_WRITE]), 401, "accessing a read-write endpoint with an invalid token should be rejected"),
    (MockConfig(valid=True, scopes=[]), 403, _scope_error("read-write", "no", "rejected")),
    (MockConfig(valid=True, scopes=[SCOPE_READ_ONLY]), 403, _scope_error("read-write", "read-only", "rejected")),
    (MockConfig(valid=True, scopes=[SCOPE_READ_WRITE]), 200, _scope_error("read-write", "read-write", "accepted")),
]


@pytest.mark.parametrize('token_mock_config,expected_status,error_message', SCOPE_RO_ACCESS_TEST_DATA)
def test_management_token_access_scopes_readonly(process,
                                                 expected_status: int,
                                                 error_message: str):
    """ This tests access to a read-only endpoint using different tokens.

    For each token, a GET request is made to the predefined endpoint and the
    response is checked against an expected value.
    This should be an endpoint that always succeeds, for example listing groups.
    """
    resp = requests.get(f"{SERVER}/{TEST_RO_ENDPOINT}", headers={
        "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    })
    assert resp.status_code == expected_status, error_message


@pytest.mark.parametrize('token_mock_config,expected_status,error_message', SCOPE_RW_ACCESS_TEST_DATA)
def test_management_token_access_scopes_readwrite(process,
                                                  expected_status: int,
                                                  error_message: str):
    """ This tests access to a read-write endpoint using different tokens.

    For each token, a POST request is made to the predefined endpoint with a
    generic payload and the response is checked against an expected value.
    The endpoint/payload combination must always succeed.
    """
    resp = requests.post(f"{SERVER}/{TEST_RW_ENDPOINT}", headers={
        "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    }, json=TEST_RW_DATA)
    assert resp.status_code == expected_status, error_message


@pytest.mark.parametrize('token_mock_config,expected_status,error_message', SCOPE_RO_ACCESS_TEST_DATA)
@pytest.mark.parametrize('configure_token_mock', ["http://127.0.0.1:65535/"])
def test_inaccessible_auth_server_readonly(process,
                                           expected_status: int,
                                           error_message: str,
                                           token_mock_config: MockConfig):
    """ Test server behavior when the authentication server is inaccessible,
        read-only endpoint variant.

    This is equivalent to the above read-only endpoint test, however
    in this scenario we simulate the server not having access to the
    authentication server.

    In all cases, this should be a reject. The arguments are explicitly
    unused, we just reuse the test data as it's convenient.

    As we override the fixture for configuring the token server mock,
    the test must also take `token_mock_config` as the argument would
    be unused otherwise.
    """
    resp = requests.get(f"{SERVER}/{TEST_RO_ENDPOINT}", headers={
        "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    })
    assert resp.status_code == 401, ("the server should reject any request to read-only endpoints "
                                     "when the authentication server is unavailable")


@pytest.mark.parametrize('token_mock_config,expected_status,error_message', SCOPE_RW_ACCESS_TEST_DATA)
@pytest.mark.parametrize('configure_token_mock', ["http://127.0.0.1:65535/"])
def test_inaccessible_auth_server_readwrite(process,
                                            expected_status: int,
                                            error_message: str,
                                            token_mock_config: MockConfig):
    """ Test server behavior when the authentication server is inaccessible,
        read-write endpoint variant.

    Analogous to the above test method, but testing is done
    on an RW endpoint instead.
    """
    resp = requests.post(f"{SERVER}/{TEST_RW_ENDPOINT}", headers={
        "Authorization": "Bearer token=AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    }, json=TEST_RW_DATA)
    assert resp.status_code == 401, ("the server should reject any request to read-write endpoints "
                                     "when the authentication server is unavailable")
