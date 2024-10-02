import pytest
import os
import subprocess
from pathlib import Path
import pg_temp
from common import (
    DBPATH,
    SERVER_WAIT_TIMEOUT,
    SERVER,
    wait_for_api,
    ProcessConfig,
)


def pytest_addoption(parser):
    parser.addoption("--sqlite", action="store_true", help="run tests only with sqlite")
    parser.addoption("--postgres", action="store_true", help="run tests only with postgres")


def pytest_generate_tests(metafunc):
    if "process" in metafunc.fixturenames:
        fixtures = []
        if metafunc.config.getoption("sqlite"):
            fixtures.append("db_sqlite")
        if metafunc.config.getoption("postgres"):
            fixtures.append("db_postgres")
        metafunc.parametrize("db",
                             fixtures if fixtures else
                             [
                                "db_sqlite",
                                "db_postgres",
                             ]
        )

    elif "process_gunicorn" in metafunc.fixturenames:
        if metafunc.config.getoption("sqlite"):
            metafunc.parametrize(
                "db",
                ["db_sqlite"]
            )
        else:
            # Defaults to postgres
            metafunc.parametrize(
                "db",
                ["db_postgres"]
            )


@pytest.fixture()
def db_sqlite():
    """Fixture that returns an sqlite connstring
    """
    if os.path.isfile(DBPATH):
        os.remove(DBPATH)
    return f"sqlite:///{DBPATH}"


@pytest.fixture()
def db_postgres():
    """Fixure that returns a postgres connstring
    """
    dbname = DBPATH.split('.')[0].replace('-','_')
    temp_db = pg_temp.TempDB(databases=[dbname])
    yield f'postgresql:///{dbname}?host={temp_db.pg_socket_dir}'
    temp_db.cleanup()


@pytest.fixture()
def process_config():
    """A default empty ProcessConfig passed unless
        test is parameterized like so:

        **Example usage**

        .. sourcecode:: python
            @pytest.mark.parametrize("process_config", [ProcessConfig(no_ssl=False)])
            test_dummy(process):
                pass
    """
    return ProcessConfig()


@pytest.fixture(scope="function")
def process(db, process_config: ProcessConfig, request):
    """Fixture to start the RDFM server with Werkzeug"""

    log_file = (Path(__file__).parent / "server.log").open("a")

    args = [
            "poetry",
            "run",
            "python3",
            "-m",
            "rdfm_mgmt_server",
            "--database",
            request.getfixturevalue(db),
        ]

    if process_config.insert_mocks:
        args.append("--test-mocks")
    if process_config.no_ssl:
        args.append("--no-ssl")
    if process_config.no_api_auth:
        args.append("--no-api-auth")
    if process_config.debug:
        args.append("--debug")

    print("Starting server..")
    process = subprocess.Popen(
        args,
        stdout=log_file,
        stderr=log_file,
    )
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()
    log_file.close()


@pytest.fixture(scope="function")
def process_gunicorn(db, request):
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
            "RDFM_DB_CONNSTRING": request.getfixturevalue(db),
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
