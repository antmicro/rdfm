import re
import os
from typing import Optional
from pathlib import Path
from argparse import ArgumentParser, ArgumentTypeError, Namespace


DEFAULT_CONSUMER_CONFIG = "example_consumer_config.json"
DEFAULT_KEYCLOAK_CONFIG = "example_keycloak_config.json"
POLL_TIMEOUT_MS = 100
HOST_PATTERN = re.compile("^(?:[0-9a-zA-Z\\-%._]*://)?\\[?([0-9a-zA-Z\\-%._:]*)]?:([0-9]+)")


def validate_bootstrap_server(url: str) -> Optional[str]:
    matched = HOST_PATTERN.match(url)
    return f"{matched.group(1)}:{matched.group(2)}" if matched else None


def check_float_abs(value: str) -> float:
    """
    Checks if the provided argument is a float, returns its absolute value.
    """
    try:
        n = float(value)
    except ValueError:
        raise Exception(f"{value} is not a float")
    return abs(n)


def validate_capture_group(args: Namespace) -> bool:
    """
    Checks whether the provided arguments related to capturing data from log entries make sense
    """
    if args.plot and not args.pattern:
        print('Named argument "--pattern" is requried when in plot mode')
        return False
    if args.plot or (args.print and args.pattern):
        if args.pattern.groups < args.group:
            print((f"Expression {args.pattern.pattern} has {args.pattern.groups}"
                   f" group(s), less than {args.group}"))
            return False
    return True


def str_to_bytes(key: str) -> bytes:
    """
    In Kafka, key is a byte array.
    """
    return key.encode("utf-8")


def check_regex_compiles(expr: str) -> re.Pattern:
    """
    Check if the provided reguar expression compiles and if it has capture groups.
    """
    try:
        pattern = re.compile(expr)
        if pattern.groups < 1:
            raise ArgumentTypeError(f"{expr} does not contain capture groups")
    except re.error:
        raise Exception(f"{expr} is not a valid regular expression")
    return pattern


def check_gt_0(value: str) -> int:
    """
    Check if a provided argument is an integer greater than 0, if it then it can describe
    a capture group index.
    """
    try:
        n = int(value)
        if n < 1:
            raise ArgumentTypeError(f"{value} does not denote a possible capture group")
    except ValueError:
        raise Exception(f"{value} is not an int")
    return n


def bootstrap_servers(servers: str) -> list[str]:
    validated = []
    for server in servers.split(","):
        v = validate_bootstrap_server(server)
        if v:
            validated.append(v)
    if not any(validated):
        raise ValueError("At least one valid bootstrap server must be provided")
    return validated


def parse_args() -> Namespace:
    parser = ArgumentParser(
            prog="rdfm-plotter",
            description="Consume messages, plot metrics")

    mode = parser.add_mutually_exclusive_group(required=True)
    cast = parser.add_mutually_exclusive_group()

    mode.add_argument("--plot", action="store_true")
    mode.add_argument("--print", action="store_true")

    cast.add_argument("-f", "--float",
                      action="store_true",
                      default=True,
                      help="When in plot mode, cast the result of the capture group into a float.")

    cast.add_argument("-i", "--int",
                      action="store_true",
                      help="When in plot mode, cast the result of the capture group into an int.")

    parser.add_argument("-d", "--device",
                        type=str,
                        required=True,
                        help=("String with a valid MAC address of the"
                              " device of which metrics to consume."))

    parser.add_argument("-t", "--topic")  # device will mean the same thing as --topic in the future

    parser.add_argument("-k", "--key",
                        type=str_to_bytes,
                        default=None,
                        help=("String that's later converted to a byte array. Specifies the"
                              " key of messages which will not be filtered out when consuming."))

    parser.add_argument("-o", "--offset-hours",
                        type=check_float_abs,
                        default=0.0,
                        help=("Non-negative floating point value. Specifies if, and how far back"
                              " the consumer should jump before it starts consuming messages."))

    parser.add_argument("-p", "--pattern",
                        type=check_regex_compiles,
                        default=None,
                        help=("Regular expression containing at least one capture group. Required"
                              " in plot mode, optional in print mode."))

    parser.add_argument("-g", "--group",
                        type=check_gt_0,
                        default=1,
                        help=("Capture group index starting from 1. Denotes which group"
                              " to retrive from the specified pattern. Can't be greater"
                              " than the number of groups in pattern."))

    parser.add_argument("--poll-timeout",
                        type=check_gt_0,
                        default=POLL_TIMEOUT_MS,
                        help="Broker polling timeout when plotting in milliseconds.")

    parser.add_argument("--plain",
                        default=False,
                        action="store_true",
                        help="Creates a plaintext consumer")

    parser.add_argument("-b", "--bootstrap-servers",
                        type=bootstrap_servers,
                        help='Comma separated list of "hostname:port"')

    parser.add_argument("-c", "--consumer-config", default=DEFAULT_CONSUMER_CONFIG)
    parser.add_argument("-C", "--keycloak-config", default=DEFAULT_KEYCLOAK_CONFIG)

    args = parser.parse_args()

    assert validate_capture_group(args)
    consumer_config_path = Path(args.consumer_config)
    if not args.plain:
        # When not running the consumer PLAINTEXT
        # use the configuration files for OAUTH and SSL
        keycloak_config_path = Path(args.keycloak_config)
        assert keycloak_config_path.is_file()
        assert consumer_config_path.is_file()
    else:
        # When running the consumer PLAINTEXT
        # we just require the bootstrap servers
        assert args.bootstrap_servers or consumer_config_path.is_file()

    return args
