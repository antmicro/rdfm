import pytest
import time
import signal
import subprocess
from rdfm_plotter.log_pb2 import log as Log
from rdfm_plotter.rdfm_consumer import (
    RdfmConsumer,
    ClientConfiguration
)


DEFAULT_TIMEOUT_S = 10


def test_print(simple_produce_50, mgmt_endpoint):
    """
    Print records in topic and exit with 0 if sent a SIGINT
    """
    args = [
            "poetry", "run", "rdfm-plotter", "--print", "--plain",
            "--bootstrap-servers", mgmt_endpoint,
            "--device", "00:00:00:00:00:00",
            "--topic", simple_produce_50,
            "--offset-hours", "0.5"
            ]

    with pytest.raises(subprocess.TimeoutExpired):
        try:
            subprocess.check_call(args, timeout=DEFAULT_TIMEOUT_S)
        except subprocess.CalledProcessError as e:
            pytest.fail(f"rdfm-plotter should not return a non-zero code, got: {e.returncode}")


def test_plot(simple_produce_50, mgmt_endpoint):
    """
    Plot records from the last half hour (broker time) and exit with 0
    """
    args = [
            "poetry", "run", "rdfm-plotter", "--plot", "--plain",
            "--bootstrap-servers", mgmt_endpoint,
            "--device", "00:00:00:00:00:00",
            "--topic", simple_produce_50,
            "--offset-hours", "0.5",
            "--pattern", "([0-9]+)"
            ]

    try:
        process = subprocess.run(args, timeout=DEFAULT_TIMEOUT_S)
        assert 0 == process.returncode, "records should be plotted successfully"
    except subprocess.TimeoutExpired as e:
        pytest.fail("rdfm-plotter reached the default timeout")


def test_incorrect_capture_groups(produce_test_key_50, mgmt_endpoint):
    """
    Wrong pattern capture causes the plotter to notice it has nothing to plot.
    Should notify in stdout and exit with 0.
    """
    args = [
            "poetry", "run", "rdfm-plotter", "--plot", "--plain",
            "--bootstrap-servers", mgmt_endpoint,
            "--device", "00:00:00:00:00:00",
            "--topic", produce_test_key_50,
            "--offset-hours", "0.5",
            "--pattern", "wrong_key=([0-9]+)"  # This won't capture anything
            ]

    try:
        output = subprocess.check_output(args, text=True, timeout=DEFAULT_TIMEOUT_S)
        assert "nothing to plot" in output, \
               "rdfm-plotter should notify that it found nothing to plot"
    except subprocess.TimeoutExpired as e:
        pytest.fail("rdfm-plotter reached the default timeout")


def test_invalid_capture_group_index(mgmt_endpoint):
    """
    An assertion should fail when provided a group index that doesn't make sense.
    """
    args = [
            "poetry", "run", "rdfm-plotter", "--print", "--plain",
            "--bootstrap-servers", mgmt_endpoint,
            "--device", "00:00:00:00:00:00",
            "--topic", "dummy",
            "--pattern", "some_key=([0-9]+)",  # One capture group
            "--group", "2"  # Capture group index 2
            ]

    try:
        subprocess.check_output(args, stderr=subprocess.STDOUT, text=True, timeout=DEFAULT_TIMEOUT_S)
    except subprocess.CalledProcessError as e:
        assert "has 1 group(s), less than 2" in e.output
        assert 1 == e.returncode
