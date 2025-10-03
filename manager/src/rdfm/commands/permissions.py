import argparse
import rdfm.config
from typing import List
import rdfm.api.permissions
import rdfm.permissions
import re

MAC_ADDR_REGEX = "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
PERMISSIONS_CHOICES = [rdfm.permissions.READ_PERMISSION,
                       rdfm.permissions.CREATE_PERMISSION,
                       rdfm.permissions.UPDATE_PERMISSION,
                       rdfm.permissions.DELETE_PERMISSION,
                       rdfm.permissions.SHELL_PERMISSION]
RESOURCE_CHOICES = [rdfm.permissions.GROUP_RESOURCE,
                    rdfm.permissions.PACKAGE_RESOURCE,
                    rdfm.permissions.DEVICE_RESOURCE]


def list_permissions(config: rdfm.config.Config, args):
    """CLI entrypoint - listing permissions"""
    permissions: List[rdfm.api.permissions.Permission] = (rdfm.api.permissions
                                                          .fetch_all(config))

    def filter_cmp(permission, cmp_val):
        return not cmp_val or permission == cmp_val

    filtered: List[rdfm.api.permissions.Permission] = list(filter(
        lambda perm: (filter_cmp(perm.user_id, args.user) and
                      filter_cmp(perm.resource, args.resource) and
                      filter_cmp(perm.resource_id, args.resource_id) and
                      filter_cmp(perm.permission, args.permission)),
        permissions
    ))

    if len(filtered) > 0:
        print("Permissions:")
        for permission in filtered:
            print(f"Permission id: {permission.id}")
            print(f"Permission type: {permission.permission}")
            print(f"Resource type: {permission.resource}")
            print(f"Resource id: {permission.resource_id}")
            print(f"User id: {permission.user_id}")
            print(f"Created: {permission.created}")
            print()


def resolve_device_identifier(config: rdfm.config.Config, identifier: str):
    devices: List[rdfm.api.devices.Device] = rdfm.api.devices.fetch_all(config)

    if re.fullmatch(MAC_ADDR_REGEX, identifier):
        filtered: rdfm.api.devices.Device = list(
            filter(lambda device: device.mac_address == identifier, devices))
    elif identifier.isdigit():
        filtered: rdfm.api.devices.Device = list(
            filter(lambda device: device.id == int(identifier), devices))
    else:
        filtered: rdfm.api.devices.Device = list(
            filter(lambda device: device.name == identifier, devices))

    return filtered[0].id if len(filtered) != 0 else None


def resolve_resource_identifier(config: rdfm.config.Config, resource: str,
                                id: str):
    match resource:
        case rdfm.permissions.DEVICE_RESOURCE:
            resources = rdfm.api.devices.fetch_all(config)
            id = resolve_device_identifier(config, id)
        case rdfm.permissions.GROUP_RESOURCE:
            resources = rdfm.api.groups.fetch_all(config)
        case rdfm.permissions.PACKAGE_RESOURCE:
            resources = rdfm.api.packages.fetch_all(config)

    filtered = list(filter(lambda res: res.id == int(id), resources))

    return filtered[0].id if len(filtered) != 0 else None


def add_permissions(config: rdfm.config.Config, args):
    """CLI entrypoint - adding permissions"""
    err = False
    for id in args.id:
        resolved_id = resolve_resource_identifier(config, args.resource, id)
        if not resolved_id:
            print(f"{args.resource} with identifier {id} does not exist")
            continue
        for user in args.user:
            for permission in args.permission:
                ret = rdfm.api.permissions.add_permission(config,
                                                          args.resource,
                                                          resolved_id, user,
                                                          permission)
                if ret:
                    print(ret)
                    err = True
    if err:
        raise RuntimeError(f"failed to add permissions")


def remove_permissions(config: rdfm.config.Config, args):
    """CLI entrypoint - removing permissions"""
    permissions: List[rdfm.api.permissions.Permission] = (rdfm.api.permissions
                                                          .fetch_all(config))
    if args.id:
        resolved_ids = []
        for id in args.id:
            resolved_id = resolve_resource_identifier(config, args.resource,
                                                      id)
            if not resolved_id:
                print(f"{args.resource} with identifier {id} does not exist")
                continue
            resolved_ids.append(resolved_id)

    def resource_id_check(id):
        return id in resolved_ids if not args.all_ids else True

    filtered: List[rdfm.api.permissions.Permission] = list(
        filter(lambda perm: (perm.resource == args.resource and
                             resource_id_check(perm.resource_id) and
                             perm.user_id in args.user and
                             perm.permission in args.permission),
               permissions)
    )

    err = False
    for permission in filtered:
        ret = rdfm.api.permissions.remove_permission(config,
                                                     permission.id)
        if ret:
            print(ret)
            err = True

    if err:
        raise RuntimeError(f"failed to remove permissions")


def add_permissions_parser(parser: argparse._SubParsersAction):
    """Create a parser for the `permissions` CLI command tree within
        the given subparser.

    Args:
        parser: subparser object created using `add_subparsers`
    """
    permissions = parser.add_parser("permissions",
                                    help="permission management")
    sub = permissions.add_subparsers(required=True,
                                     title="permission commands")

    list = sub.add_parser("list", help="list all permissions")
    list.set_defaults(func=list_permissions)
    list.add_argument("--user", type=str, help="filter by user id")
    list.add_argument("--resource", type=str, choices=RESOURCE_CHOICES,
                      help="filter by resource type")
    list.add_argument("--resource-id", type=int, help="filter by resource id")
    list.add_argument("--permission", type=str, choices=PERMISSIONS_CHOICES,
                      help="filter by permission type")

    create = sub.add_parser("create", help="create permission")
    create.set_defaults(func=add_permissions)
    create.add_argument(
        "resource", type=str, choices=RESOURCE_CHOICES,
        help="resource type"
    )
    create.add_argument(
        "--id", type=str, nargs="+", help="resource ids", required=True
    )
    create.add_argument(
        "--user", type=str, nargs="+", help="user ids", required=True
    )
    create.add_argument(
        "--permission", type=str, nargs="+", choices=PERMISSIONS_CHOICES,
        help="permission types", required=True
    )

    delete = sub.add_parser("delete", help="delete permission")
    delete.set_defaults(func=remove_permissions)
    delete.add_argument(
        "resource", type=str, choices=RESOURCE_CHOICES,
        help="resource type"
    )
    delete_ids = delete.add_mutually_exclusive_group(required=True)
    delete_ids.add_argument(
        "--id", type=str, nargs="+", help="resource ids"
    )
    delete_ids.add_argument(
        "--all-ids", action='store_true', help="all resource ids"
    )
    delete.add_argument(
        "--user", type=str, nargs="+", help="user ids", required=True
    )
    delete.add_argument(
        "--permission", type=str, nargs="+", choices=PERMISSIONS_CHOICES,
        help="permission types", required=True
    )
