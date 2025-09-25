import pytest
import time
import os
import re
import subprocess
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from rdfm_plotter.log_pb2 import log as Log


KAFKA_CLUSTER_ID = "foobarbaz"
KAFKA_CONFIG_REL_PATH = Path("server.properties")
DEVICE = "00:00:00:00:00:00"
TOPIC = "00-00-00-00-00-00"
SINGULARITY_IMAGE = "test_kafka.sif"
DEFAULT_TIMEOUT_S = 15
DEFAULT_INTERVAL_S = 1


def wait_for_broker(broker: str,
                    timeout: int = DEFAULT_TIMEOUT_S,
                    interval: int = DEFAULT_INTERVAL_S) -> bool:
    start = time.time()
    while True:
        try:
            producer = KafkaProducer(bootstrap_servers=broker)
            producer.close()
            return True
        except NoBrokersAvailable:
            if time.time() - start > timeout:
                return False
            print("Broker not available, waiting...")
            time.sleep(interval)


def find_endpoint_in_cfg(listener: str, cwd: Path, kafka_config_rel_path: Path) -> str:
    with open(cwd / kafka_config_rel_path) as f:
        pattern = f"{re.escape(listener)}:\\/\\/([A-Za-z0-9\\.]+:[0-9]+)"
        match = re.search(pattern, f.read())
        assert match is not None, f"searching {kafka_config_rel_path} must yield a result"
        assert match.groups()[0], f"searching {kafka_config_rel_path} must yield a result"
        return match.groups()[0]


def log_serializer(log: Log) -> bytes:
    # Ignore the method name, it returns bytes
    return log.SerializeToString()


def pytest_addoption(parser):
    parser.addoption("--testpath", action="store", default=os.getcwd())


def pytest_generate_tests(metafunc):
    testpath_value = metafunc.config.option.testpath
    if "testpath" in metafunc.fixturenames and testpath_value is not None:
        metafunc.parametrize("testpath", [Path(testpath_value)], scope="session")


@pytest.fixture(scope="session")
def get_rdfm_jwt_secret(testpath: Path) -> str:
    assert (testpath / Path(SINGULARITY_IMAGE)).is_file(), f"{SINGULARITY_IMAGE} needs to be built"

    pattern = re.compile("RDFM_JWT_SECRET=(.+)")

    args = [
            "apptainer",
            "inspect",
            "--environment", SINGULARITY_IMAGE,
            ]

    segments = subprocess.check_output(args, cwd=testpath, text=True).split()
    match = None
    for s in segments:
        match = pattern.match(s)
        if match:
            break

    return match.group(1)


@pytest.fixture(scope="session")
def dev_endpoint(testpath: Path) -> str:
    """
    Looks at the config located at f"{testpath}/{KAFKA_CONFIG_REL_PATH}"
    and finds the device endpoint address. For example, if the endpoint
    declared in the config is: "DEV://192.168.1.100:9094" this fixture
    will be a string containing "192.168.1.100:9094".
    """
    return find_endpoint_in_cfg("DEV", testpath, KAFKA_CONFIG_REL_PATH)


@pytest.fixture(scope="session")
def mgmt_endpoint(testpath: Path) -> str:
    """
    Looks at the config located at f"{testpath}/{KAFKA_CONFIG_REL_PATH}"
    and finds the device endpoint address. For example, if the endpoint
    declared in the config is: "MGMT://192.168.1.100:9094" this fixture
    will be a string containing "192.168.1.100:9094".
    """
    return find_endpoint_in_cfg("MGMT", testpath, KAFKA_CONFIG_REL_PATH)


@pytest.fixture
def broker(testpath, dev_endpoint, mgmt_endpoint):
    INSTANCE_NAME = "test_kafka_instance"
    dev_port = dev_endpoint.split(":")[-1]
    mgmt_port = mgmt_endpoint.split(":")[-1]

    assert (testpath / Path(SINGULARITY_IMAGE)).is_file(), f"{SINGULARITY_IMAGE} needs to be built"

    args = [
            "apptainer",
            "instance",
            "start",
            "--net",
            f'--network-args=portmap={dev_port}:{dev_port}/tcp,portmap={mgmt_port}:{mgmt_port}/tcp',
            "--contain",
            "--writable-tmpfs",
            SINGULARITY_IMAGE,
            INSTANCE_NAME,
            ]

    result = subprocess.run(args, cwd=testpath)
    assert 0 == result.returncode, f"{INSTANCE_NAME} should have started successfully"

    assert wait_for_broker(mgmt_endpoint), "broker must start successfully"

    yield None

    args = [
            "apptainer",
            "instance",
            "stop",
            INSTANCE_NAME,
            ]

    result = subprocess.run(args)
    assert 0 == result.returncode, f"{INSTANCE_NAME} should have stopped successfully"


@pytest.fixture
def create_topic(testpath, broker, mgmt_endpoint) -> str:
    args = [
        "apptainer", "exec", SINGULARITY_IMAGE,
        "/opt/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", mgmt_endpoint,
        "--topic", TOPIC,
        "--create",
        "--partitions", "1",
        "--replication-factor", "1"
    ]

    result = subprocess.run(args, cwd=testpath)
    assert 0 == result.returncode
    return TOPIC


@pytest.fixture
def mgmt_producer(create_topic, mgmt_endpoint):
    p = KafkaProducer(bootstrap_servers=mgmt_endpoint, value_serializer=log_serializer)
    yield p
    p.close()


@pytest.fixture
def simple_produce_50(create_topic, mgmt_producer):
    for i in range(1, 50):
        log = Log(device_mac=DEVICE, entry=str(i))
        log.device_time.FromSeconds(i)
        mgmt_producer.send(topic=create_topic, value=log)
    mgmt_producer.flush()
    return create_topic


@pytest.fixture
def produce_test_key_50(create_topic, mgmt_producer):
    for i in range(1, 50):
        log = Log(device_mac=DEVICE, entry=f"test={i}")
        log.device_time.FromSeconds(i)
        mgmt_producer.send(topic=create_topic, value=log)
    mgmt_producer.flush()
    return create_topic
