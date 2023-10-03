import argparse
import rdfm.config
import requests
import rdfm.api.devices
from typing import List, Optional


def list_devices(config: rdfm.config.Config, args):
    """ CLI entrypoint - listing devices
    """
    devices: List[rdfm.api.devices.Device] = rdfm.api.devices.fetch_all(config)
    print("Registered devices:")
    for device in devices:
        print(f"Device #{device.id}")
        print(f"\tName: '{device.name}'")
        print(f"\tMAC address: {device.mac_address}")
        print("\tCapabilities:")
        for k, v in device.capabilities.items():
            print(f"\t\t{k}: {v}")
        print("\tMetadata:")
        for k, v in device.metadata.items():
            print(f"\t\t{k}: {v}")
        print(f"\tLast accessed: {device.last_access}")
        print(f"\tAssigned to group: {'<none>' if device.group is None else device.group}")
        print(f"\tPublic key: {device.public_key}")
        print()


def list_pending_devices(config: rdfm.config.Config, args):
    """ CLI entrypoint - listing pending devices (awaiting registration)
    """
    print("Registration requests:")
    pending: List[rdfm.api.devices.Registration] = rdfm.api.devices.fetch_registrations(config)
    for request in pending:
        print("Request:")
        print(f"\tMAC address: {request.mac_address}")
        print(f"\tPublic key: {request.public_key}")
        print(f"\tLast appeared on: {request.last_appeared}")
        print(f"\tMetadata:")
        for k, v in request.metadata.items():
            print(f"\t\t{k}: {v}")
        print()


def auth_device(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - authorizing a device
    """
    mac_address = args.device_id
    pending: List[rdfm.api.devices.Registration] = rdfm.api.devices.fetch_registrations(config)

    requests = list(req for req in pending if req.mac_address == mac_address)
    for idx, request in enumerate(requests):
        if request.mac_address != mac_address:
            continue
        print(f"Request {idx}:")
        print(f"\tMAC address: {request.mac_address}")
        print(f"\tPublic key: {request.public_key}")
        print(f"\tLast appeared on: {request.last_appeared}")
        print(f"\tMetadata:")
        for k, v in request.metadata.items():
            print(f"\t\t{k}: {v}")
        print()

    if len(requests) == 0:
        return "No requests for devices matching the specified MAC address"

    if len(requests) > 1:
        print("Which registration request should be approved?")
        idx = int(input("> "))
    else:
        idx = 0
    chosen = requests[idx]

    print(f"Approving device with MAC {mac_address} and public key {chosen.public_key}")
    return rdfm.api.devices.approve(config,
                                    mac_address,
                                    chosen.public_key)


def deauth_device(config: rdfm.config.Config, args):
    """ CLI entrypoint - de-authorizing a device
    """
    print("Deauthorizing devices unsupported")


def shell_to_device(config: rdfm.config.Config, args):
    """ CLI entrypoint - shell to a device
    """
    print("Shell to devices unimplemented")


def add_devices_parser(parser: argparse._SubParsersAction):
    """ Create a parser for the `devices` CLI command tree within
        the given subparser.

    Args:
        parser: subparser object created using `add_subparsers`
    """
    devices = parser.add_parser('devices', help='device management')
    sub = devices.add_subparsers(required=True, title='device commands')

    list = sub.add_parser('list', help='list all registered devices')
    list.set_defaults(func=list_devices)

    list_pending = sub.add_parser('pending', help='list all pending devices (awaiting approval)')
    list_pending.set_defaults(func=list_pending_devices)

    auth = sub.add_parser('auth', help='authorize a device to access the server')
    auth.set_defaults(func=auth_device)
    auth.add_argument('device_id', type=str,
                      help='device identifier of the device')

    deauth = sub.add_parser('deauth', help='remove authorization of a device to the server')
    deauth.set_defaults(func=deauth_device)
    deauth.add_argument('device_id', type=str,
                        help='device identifier of the device')

    shell = sub.add_parser('shell', help='connect to a shell on the device')
    shell.set_defaults(func=shell_to_device)
    shell.add_argument('device_id', type=str,
                       help='device identifier of the device')
