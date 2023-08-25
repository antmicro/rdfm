import argparse
import rdfm.config
import requests


def list_devices(config: rdfm.config.Config, args):
    """ CLI entrypoint - listing devices
    """
    print("Listing devices unsupported")


def auth_device(config: rdfm.config.Config, args):
    """ CLI entrypoint - authorizing a device
    """
    print("Authorizing devices unsupported")


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

    list = sub.add_parser('list', help='list all pending and registered devices')
    list.set_defaults(func=list_devices)

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
