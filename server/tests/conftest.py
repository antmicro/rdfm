import pytest
import os
import subprocess
from pathlib import Path
from common import (
    DBPATH,
    SERVER_WAIT_TIMEOUT,
    SERVER,
    wait_for_api,
)


@pytest.fixture(scope="function")
def process():
    """Fixture to start the RDFM server with Werkzeug"""

    if os.path.isfile(DBPATH):
        os.remove(DBPATH)
    log_file = (Path(__file__).parent / "server.log").open("a")

    print("Starting server..")
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "rdfm_mgmt_server",
            "--no-ssl",
            "--no-api-auth",
            "--test-mocks",
            "--database",
            f"sqlite:///{DBPATH}",
        ],
        stdout=log_file,
        stderr=log_file,
    )
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()
    log_file.close()


@pytest.fixture(scope="function")
def process_gunicorn():
    """Fixture to start the RDFM server with Gunicorn"""

    if os.path.isfile(DBPATH):
        os.remove(DBPATH)
    log_file = (Path(__file__).parent / "server_gunicorn.log").open("a")

    print("Starting server..")
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "gunicorn",
            "-k",
            "gevent",
            "-b",
            "localhost:5000",
            "rdfm_mgmt_server:setup_with_config_from_env()",
        ],
        env={
            "RDFM_HOSTNAME": "localhost",
            "RDFM_API_PORT": "5000",
            "RDFM_DB_CONNSTRING": f"sqlite:///{DBPATH}",
            "RDFM_LOCAL_PACKAGE_DIR": "/tmp/.rdfm-local-storage",
            "RDFM_DISABLE_ENCRYPTION": "1",
            "RDFM_DISABLE_API_AUTH": "1",
            **os.environ
        },
        stdout=log_file,
        stderr=log_file,
    )
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()
    log_file.close()


@pytest.fixture(scope="session")
def install_manager_to_venv():
    """Required for running rdfm-mgmt within it's own venv"""
    process = subprocess.Popen(["poetry", "-C", "../manager/", "install"])
    code: int = process.wait()
    assert code == 0, "manager should be installed in the .venv"
