import pytest
import os
import re
import subprocess
from pathlib import Path
import pg_temp
import sqlalchemy
from common import (
    DBPATH,
    SERVER_WAIT_TIMEOUT,
    SERVER,
    wait_for_api,
    ProcessConfig,
)
# Imports for Kafka integration
from common import (
    find_endpoint_in_cfg,
    wait_for_broker,
    KAFKA_CONFIG_REL_PATH,
    KAFKA_SINGULARITY_IMAGE,
    KAFKA_TOPIC,
)
from device_mgmt.pubsub import RdfmKafkaAdminClient


def pytest_addoption(parser):
    parser.addoption("--sqlite", action="store_true", help="run tests only with sqlite")
    parser.addoption("--postgres", action="store_true", help="run tests only with postgres")
    parser.addoption("--sifpath", action="store")
    parser.addoption("--alembic-script-location", action="store")
    parser.addoption("--alembic-file", action="store")


def parametrize_path_option(metafunc, option_name, default_value=None):
    """
    Turns a passed option which points to a path into a Path object contained within a fixture.
    """
    fixture_name = option_name.replace("-", "_")  # Hyphens not allowed!
    try:
        value = getattr(metafunc.config.option, fixture_name)
    except AttributeError:
        value = None

    value = value if value else default_value
    if value and fixture_name in metafunc.fixturenames:
        metafunc.parametrize(fixture_name, [Path(value)], scope="session")


def pytest_generate_tests(metafunc):
    if "process" in metafunc.fixturenames or "alembic_engine" in metafunc.fixturenames:
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
    # Singularity file containing Kafka
    sifpath_value = metafunc.config.option.sifpath
    if "sifpath" in metafunc.fixturenames and sifpath_value is not None:
        metafunc.parametrize("sifpath", [Path(sifpath_value)], scope="session")

    parametrize_path_option(metafunc, "alembic-file", default_value="./deploy/alembic.ini")
    parametrize_path_option(metafunc, "alembic-script-location", default_value="./alembic")


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

    additional_env = {}

    if process_config.insert_mocks:
        args.append("--test-mocks")
    if process_config.no_ssl:
        args.append("--no-ssl")
    if process_config.no_api_auth:
        args.append("--no-api-auth")
    if process_config.debug:
        args.append("--debug")
    if process_config.enable_pubsub:
        args.append("--enable-pubsub")
        additional_env.update({"JWT_SECRET": request.getfixturevalue("get_rdfm_jwt_secret"),  # Make it the same as in the .sif file
                               "RDFM_DEV_BOOTSTRAP_SERVERS": request.getfixturevalue("dev_endpoint"),
                               "RDFM_MGMT_BOOTSTRAP_SERVERS": request.getfixturevalue("mgmt_endpoint")})


    print("Starting server..")
    process = subprocess.Popen(
        args,
        env={**os.environ, **additional_env},
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
            "--timeout",    # On CPU constrained containers the workers may exceed the default timeout of 30 seconds, which fails the test.
            "3600",         # HACK: Since this is a stress test, increasing the timeout to an arbitrary big value will suffice.
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
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
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


@pytest.fixture(scope="function")
def redis_server():
    """Fixture to start a Redis server."""
    import redis
    import time

    log_file = (Path(__file__).parent / "server_redis.log").open("a")

    process = subprocess.Popen(
        ["redis-server", "--port", "6379", "--save", "", "--appendonly", "no"],
        stdout=log_file,
        stderr=log_file,
    )

    client = redis.Redis(host="localhost", port=6379)
    for _ in range(50):
        try:
            client.ping()
            break
        except redis.exceptions.ConnectionError:
            time.sleep(0.1)
    else:
        process.kill()
        raise RuntimeError("Redis server failed to start")

    yield process

    process.terminate()
    log_file.close()


@pytest.fixture(scope="session")
def install_manager_to_venv():
    """Required for running rdfm-mgmt within it's own venv"""
    process = subprocess.Popen(["poetry", "-C", "../manager/", "install"])
    code: int = process.wait()
    assert code == 0, "manager should be installed in the .venv"


@pytest.fixture(scope="session")
def get_rdfm_jwt_secret(sifpath: Path) -> str:
    assert (sifpath / Path(KAFKA_SINGULARITY_IMAGE)).is_file(), f"{KAFKA_SINGULARITY_IMAGE} needs to be built"

    pattern = re.compile("RDFM_JWT_SECRET=(.+)")

    args = [
            "apptainer",
            "inspect",
            "--environment", KAFKA_SINGULARITY_IMAGE,
            ]

    segments = subprocess.check_output(args, cwd=sifpath, text=True).split()
    match = None
    for s in segments:
        match = pattern.match(s)
        if match:
            break

    return match.group(1)


@pytest.fixture(scope="session")
def dev_endpoint(sifpath: Path) -> str:
    """
    Looks at the config located at f"{sifpath}/{KAFKA_CONFIG_REL_PATH}"
    and finds the device endpoint address. For example, if the endpoint
    declared in the config is: "DEV://192.168.1.100:9094" this fixture
    will be a string containing "192.168.1.100:9094".
    """
    return find_endpoint_in_cfg("DEV", sifpath, KAFKA_CONFIG_REL_PATH)


@pytest.fixture(scope="session")
def mgmt_endpoint(sifpath: Path) -> str:
    """
    Looks at the config located at f"{sifpath}/{KAFKA_CONFIG_REL_PATH}"
    and finds the device endpoint address. For example, if the endpoint
    declared in the config is: "MGMT://192.168.1.100:9094" this fixture
    will be a string containing "192.168.1.100:9094".
    """
    return find_endpoint_in_cfg("MGMT", sifpath, KAFKA_CONFIG_REL_PATH)


@pytest.fixture
def broker(sifpath, dev_endpoint, mgmt_endpoint):
    INSTANCE_NAME = "test_kafka_instance"
    dev_port = dev_endpoint.split(":")[-1]
    mgmt_port = mgmt_endpoint.split(":")[-1]

    assert (sifpath / Path(KAFKA_SINGULARITY_IMAGE)).is_file(), f"{KAFKA_SINGULARITY_IMAGE} needs to be built"

    args = [
            "apptainer",
            "instance",
            "start",
            "--net",
            f'--network-args=portmap={dev_port}:{dev_port}/tcp,portmap={mgmt_port}:{mgmt_port}/tcp',
            "--contain",
            "--writable-tmpfs",
            KAFKA_SINGULARITY_IMAGE,
            INSTANCE_NAME,
            ]

    result = subprocess.run(args, cwd=sifpath)
    assert 0 == result.returncode, f"{INSTANCE_NAME} should have started successfully"

    assert wait_for_broker(mgmt_endpoint), "broker must start successfully"

    yield sifpath

    args = [
            "apptainer",
            "instance",
            "stop",
            INSTANCE_NAME,
            ]

    result = subprocess.run(args)
    assert 0 == result.returncode, f"{INSTANCE_NAME} should have stopped successfully"


@pytest.fixture
def create_topic(broker, mgmt_endpoint) -> str:
    args = [
        "apptainer", "exec", KAFKA_SINGULARITY_IMAGE,
        "/opt/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", mgmt_endpoint,
        "--topic", KAFKA_TOPIC,
        "--create",
        "--partitions", "1",
        "--replication-factor", "1"
    ]

    result = subprocess.run(args, cwd=broker)
    assert 0 == result.returncode
    return KAFKA_TOPIC


@pytest.fixture
def rdfm_kafka_admin(create_topic, mgmt_endpoint) -> RdfmKafkaAdminClient:
    admin = RdfmKafkaAdminClient(bootstrap_servers=mgmt_endpoint,
                                 security_protocol="PLAINTEXT")
    yield admin
    admin.close()

@pytest.fixture
def alembic_config(alembic_file, alembic_script_location):
    return {
        "file": str(alembic_file),
        "script_location": str(alembic_script_location),
    }


@pytest.fixture
def alembic_engine(db, request):
    return sqlalchemy.create_engine(request.getfixturevalue(db))
