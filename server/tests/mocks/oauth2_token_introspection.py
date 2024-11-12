from multiprocessing import Process
import inspect
import subprocess
import flask
import os
import json
import requests
import typing
from flask import current_app, request
import pytest
import traceback
import time


class MockConfig():
    """ Mock configuration
    """
    # Should the introspection return a "token valid" response?
    token_valid: bool
    # List of scopes to return in the token introspection response
    token_scopes: list[str]


    def __init__(self, valid: bool = False, scopes: list[str] = [], user_id: str = "", **kwargs) -> None:
        self.token_valid = valid
        self.token_scopes = scopes
        self.user_id = user_id
        for key in kwargs:
            setattr(self, key, kwargs[key])


    def serialize(self) -> str:
        return json.dumps(vars(self))


    def deserialize(serialized: str) -> "MockConfig":
        return MockConfig(**json.loads(serialized))


""" Port on which the mock is listening on """
MOCKS_PORT = 9999
MOCKS_BASE_URL = f"http://127.0.0.1:{MOCKS_PORT}/"
MOCKS_INTROSPECT_PATH = '/token/introspect'
MOCKS_CONFIG_PATH = '/.configure-mock'
app = flask.Flask("test-oauth2-mock")
data = MockConfig()


@app.route(MOCKS_INTROSPECT_PATH, methods=['POST'])
def token_introspection_endpoint():
    global data
    # From the server's PoV, only the `active` and `scope` fields matter.
    return {
        "active": data.token_valid,
        "scope": " ".join(data.token_scopes),
        "sub": data.user_id,
    }, 200


@app.route(MOCKS_CONFIG_PATH, methods=['POST'])
def configure_mock():
    """ Simple endpoint for configuring the mock

    This just takes in the incoming JSON payload and puts it in the configuration,
    no validation is done.
    It is assumed that the user serializes an instance of the `MockConfig` structure
    using the `serialize` method.
    """
    global data
    data = MockConfig.deserialize(request.data)
    return {}, 200


def main():
    app.run(port=MOCKS_PORT, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()


@pytest.fixture
def start_token_mock():
    """ Creates a mock of the bare minimum OAuth2 API functionality
        required to test the RDFM server.

    The following are mocked:
        - Token Introspection
    """
    print("Starting OAuth2 Token Introspection mock server..")

    # Run this module in a separate interpreter process, see `main`.
    process = subprocess.Popen([
        "poetry", "run", "python3", inspect.getabsfile(inspect.currentframe())
    ])
    time.sleep(5)

    # The test expects to be passed the URL to the introspection endpoint
    yield f"{MOCKS_BASE_URL}{MOCKS_INTROSPECT_PATH}"

    print("Shutting down the token mock server..")
    process.kill()


@pytest.fixture
def configure_token_mock(start_token_mock, token_mock_config: MockConfig):
    """ Start and configure the token mock server

    Parametrize this fixture by setting the `token_mock_config` mark to the
    configuration you want (instance of the `MockConfig` class).

    NOTE: When importing this fixture, you must also import the child
    fixture `start_token_mock`.
    """
    response = requests.post(f"{MOCKS_BASE_URL}{MOCKS_CONFIG_PATH}",
                             data=token_mock_config.serialize(),
                             headers={
                                 'Content-Type': 'application/json'
                             })
    assert response.status_code == 200, "setting mock configuration should succeed"
    # Return the introspection URL to the actual test
    return start_token_mock
