import pytest
import time
import os
import re
import tempfile
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
    TEST_JWT_SECRET
)
# Imports for Kafka integration
from common import (
    find_endpoint_in_cfg,
    wait_for_broker,
    KAFKA_CONFIG_REL_PATH,
    KAFKA_SINGULARITY_IMAGE,
    KAFKA_TOPIC,
    LOCAL_PACKAGE_DIR,
)
from device_mgmt.pubsub import RdfmKafkaAdminClient


def pytest_addoption(parser):
    process_group = parser.getgroup("process")

    process_group.addoption("--external-docker",
                            action="store_true",
                            default=False,
                            help="Run the test suite without a server subprocess fixture and instead make use of a docker compose file from `server/deploy`")

    process_group.addoption("--internal-werkzeug",
                            action="store_true",
                            default=True,
                            help="Run the test suite against a server subprocess running with werkzeug")

    process_group.addoption("--internal-gunicorn",
                            action="store_true",
                            default=False,
                            help="Run the test suite against a server subprocess running with gunicorn")

    database_backend_group = parser.getgroup("database_backend")

    database_backend_group.addoption("--sqlite",
                                     action="store_true",
                                     default=False,
                                     help="Run test suite with the sqlite database backend, ignored when `--external-docker` is passed")

    database_backend_group.addoption("--postgres",
                                     action="store_true",
                                     default=False,
                                     help="Run test suite with the postgres database backend, ignored when `--external-docker` is passed")

    parser.addoption("--alembic-script-location", action="store")

    parser.addoption("--alembic-file", action="store")
    parser.addoption("--create-tmpdir-for-packages", action="store_true")

    parser.addoption("--sifpath", action="store")


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


def parametrize_database_choice_for_internal_process(metafunc):
    # The choice is made based on the presence of `sqlite` and `postgres` flag options
    # passed to pytest via CLI.
    if "db" in metafunc.fixturenames:
        fixtures = []
        if metafunc.config.getoption("sqlite"):
            fixtures.append("db_sqlite")
        if metafunc.config.getoption("postgres"):
            fixtures.append("db_postgres")
        # Defalts to running both backends back to back.
        metafunc.parametrize("db",
                             fixtures if fixtures else
                             [
                                "db_sqlite",
                                "db_postgres",
                             ]
        )


def parametrize_process_choice(metafunc):
    def parametrize_process(metafunc, process: str):
        if "process" in metafunc.fixturenames:
            metafunc.parametrize("process", [process])

    # Are we supposed to run docker compose?
    if metafunc.config.getoption("external_docker"):
        # If yes, parametrize all process fixtures to be a "process_docker_compose" string.
        # Later the fixtures will have to dynamically request the value of the fixture with that name
        # for it to evauluate.
        parametrize_process(metafunc, "process_docker_compose")

    else:
        # If no, it means we're either running the standard "process_werkzeug" or "process_gunicorn".
        # In that case there's also a need to determine what database backed should be run and to
        # ensure that alembic migrations are going to get applied.

        parametrize_process(metafunc, "process_gunicorn" if metafunc.config.getoption("internal_gunicorn") else "process_werkzeug")

        parametrize_database_choice_for_internal_process(metafunc)


def pytest_generate_tests(metafunc):
    if "local_package_dir" in metafunc.fixturenames:
        if metafunc.config.getoption("create_tmpdir_for_packages"):
            metafunc.parametrize("local_package_dir", ["create_tmpdir"], scope="session")
        else:
            metafunc.parametrize("local_package_dir", ["default_local_package_dir"], scope="session")

    # Figure out how to run the RDFM server for the test suite.
    if "setup_server" in metafunc.fixturenames:
        parametrize_process_choice(metafunc)
    else:
        parametrize_database_choice_for_internal_process(metafunc)

    parametrize_path_option(metafunc, "alembic-file", default_value="./deploy/alembic.ini")
    parametrize_path_option(metafunc, "alembic-script-location", default_value="./alembic")

    # Singularity file containing Kafka.
    sifpath_value = metafunc.config.option.sifpath
    if "sifpath" in metafunc.fixturenames and sifpath_value is not None:
        metafunc.parametrize("sifpath", [Path(sifpath_value)], scope="session")


@pytest.fixture()
def db_sqlite():
    """Fixture that returns an sqlite connstring
    """
    db_fd, temp_db_path = tempfile.mkstemp(suffix=".db", prefix="pytest_sqlite_")
    os.close(db_fd)

    yield f"sqlite:///{temp_db_path}"

    try:
        for companion in [temp_db_path, f"{temp_db_path}-wal", f"{temp_db_path}-shm"]:
            if os.path.exists(companion):
                os.remove(companion)
    except OSError:
        pass

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
    """A default ProcessConfig passed unless test is parameterized like so:

        **Example usage**

        .. sourcecode:: python
            @pytest.mark.parametrize("process_config", [ProcessConfig(no_ssl=False)])
            test_dummy(process):
                pass
    """
    return ProcessConfig()


@pytest.fixture(scope="session")
def create_tmpdir():
    """ A wrapper fixture for creating a tempfile that
        will be cleaned at the end of a testing stession
    """
    import tempfile
    tmp_dir = tempfile.TemporaryDirectory()
    yield str(tmp_dir.name)
    tmp_dir.cleanup()


@pytest.fixture(scope="session")
def default_local_package_dir():
    return LOCAL_PACKAGE_DIR


@pytest.fixture()
def db():
    return None


@pytest.fixture()
def local_package_dir():
    return None


@pytest.fixture(scope="function")
def process_werkzeug(db, process_config: ProcessConfig, local_package_dir, request):
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
            "--local-package-dir",
            request.getfixturevalue(local_package_dir)
        ]

    env = process_config.env.copy()
    env["JWT_SECRET"] = TEST_JWT_SECRET

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
        env.update({"JWT_SECRET": request.getfixturevalue("get_rdfm_jwt_secret"),  # Make it the same as in the .sif file
                    "RDFM_DEV_BOOTSTRAP_SERVERS": request.getfixturevalue("dev_endpoint"),
                    "RDFM_MGMT_BOOTSTRAP_SERVERS": request.getfixturevalue("mgmt_endpoint")})

    print("Starting server..")
    process = subprocess.Popen(
        args,
        env=env,
        stdout=log_file,
        stderr=log_file,
    )
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()
    log_file.close()


@pytest.fixture(scope="function")
def process_gunicorn(db, process_config: ProcessConfig, local_package_dir, request):
    """Fixture to start the RDFM server with Gunicorn"""

    log_file = (Path(__file__).parent / "server_gunicorn.log").open("a")

    cfg_env = process_config.env.copy()
    cfg_env["JWT_SECRET"] = TEST_JWT_SECRET
    cfg_env["RDFM_HOSTNAME"] = "localhost"
    cfg_env["RDFM_API_PORT"] = "5000"
    cfg_env["RDFM_DB_CONNSTRING"] = request.getfixturevalue(db)
    cfg_env["RDFM_LOCAL_PACKAGE_DIR"] = request.getfixturevalue(local_package_dir)
    if process_config.insert_mocks:
        cfg_env["RDFM_INSERT_TEST_MOCKS"] = "1"
    if process_config.no_ssl:
        cfg_env["RDFM_DISABLE_ENCRYPTION"] = "1"
    if process_config.no_api_auth:
        cfg_env["RDFM_DISABLE_API_AUTH"] = "1"
    if process_config.debug:
        cfg_env["RDFM_DEBUG_MODE"] = "1"
    if process_config.enable_pubsub:
        cfg_env["RDFM_ENABLE_KAFKA_INTEGRATION"] = "1"

    print("Starting server..")
    process = subprocess.Popen(
        [
            "poetry",
            "run",
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
        env=cfg_env,
        stdout=log_file,
        stderr=log_file,
    )
    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER), "server has started successfully"

    yield process

    print("Shutting down server..")
    process.kill()
    log_file.close()


@pytest.fixture(scope="function")
def process_docker_compose(process_config: ProcessConfig):
    print("Starting docker compose...")

    log_file = str(Path(__file__).parent / "server_docker_compose.log")

    optional_env_file = f"--env-file {process_config.docker_env_file}" if process_config.docker_env_file else ""

    env=""
    if process_config.insert_mocks:
        env += "TEST_MOCKS=1 "

    process = subprocess.run(
            f"{env}docker compose --file {process_config.docker_compose_file} {optional_env_file} up --detach",
            shell=True
    )

    assert wait_for_api(SERVER_WAIT_TIMEOUT, SERVER), "server has started successfully"

    assert process.returncode == 0, "docker succeeded"

    yield process

    print("Shutting down server..")

    subprocess.run(
        f"docker compose --file {process_config.docker_compose_file} {optional_env_file} logs >> {log_file}",
        shell=True
    )

    subprocess.run(
        f"docker compose --file {process_config.docker_compose_file} {optional_env_file} down --volumes",
        shell=True
    )


@pytest.fixture(scope="function")
def setup_server(process_config: ProcessConfig, db, local_package_dir, process, request):
    # Request evaluation of fixture with the name contained in the process argument.
    yield request.getfixturevalue(process)
    return


@pytest.fixture(scope="session")
def azurite_blob():
    name = "azurite_blob"

    log_file = (Path(__file__).parent / "azurite_blob.log").open("a")

    process = subprocess.Popen([
        "docker", "run", "--rm",
        "--quiet", "--name", name,
        "-a", "stdout",
        "-a", "stderr",
        "-p", "10000:10000",
        "--health-cmd", "nc 127.0.0.1 10000 -z",
        "--health-interval=1s",
        "--health-retries=30",
        "mcr.microsoft.com/azure-storage/azurite",
        "azurite-blob", "--blobHost", "0.0.0.0", "--skipApiVersionCheck"
    ],
        stdout=log_file,
        stderr=log_file
    )

    while True:
        assert process.poll() is None, "Azurite blob should not terminate unexpectedly"

        try:
            result = subprocess.run(
                        ["docker", "inspect", "--format={{json .State.Health.Status}}", name],
                        capture_output=True,
                        text=True,
                        check=True
                    )

            status = result.stdout.strip().replace('"', '')

            if status == "healthy":
                break
            elif status == "unhealthy":
                raise RuntimeError("Azurite blob isn't healthy")

            time.sleep(1)
        except subprocess.CalledProcessError:
            pass

    yield process

    process.kill()


@pytest.fixture(scope="session")
def install_manager_to_venv():
    """Required for running rdfm-mgmt within it's own venv"""
    manager_dir = os.path.join(os.path.dirname(__file__), "../../manager")
    process = subprocess.Popen(["poetry", "-C", manager_dir, "install"])
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
