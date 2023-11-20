from typing import Optional
import argparse
import rdfm.helpers
import rdfm.config
import rdfm.api.groups
from rdfm.helpers import utc_to_local


META_GROUP_NAME = "rdfm.group.name"
META_GROUP_DESC = "rdfm.group.description"


def list_groups(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - listing all groups
    """
    groups = rdfm.api.groups.fetch_all(config)

    print("Device groups:")
    for group in groups:
        print(f"Group #{group.id}")
        print(f"\tCreated at: {utc_to_local(group.created)}")
        print(f"\tDevices assigned: {group.devices} | {len(group.devices)} devices")
        print(f"\tAssigned packages: {group.packages}")
        print(f"\tUpdate policy: '{group.policy}'")
        print("\tGroup metadata:")
        for k, v in group.metadata.items():
            print(f"\t\t{k}: {v}")
        print()
    return None


def create_group(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - creating a group
    """
    # Construct group metadata from the CLI arguments
    metadata = rdfm.helpers.split_metadata(args.metadata)
    metadata[META_GROUP_NAME] = args.name
    metadata[META_GROUP_DESC] = args.description

    return rdfm.api.groups.create(config, metadata)


def delete_group(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - deleting a group
    """
    return rdfm.api.groups.delete(config, args.group_id)


def assign_package(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - assigning packages to a group
    """
    packages = [] if args.package_id is None else [ int(x) for x in args.package_id ]
    return rdfm.api.groups.assign(config,
                                  args.group_id,
                                  packages)


def modify_devices(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - modifying devices belonging to a group
    """
    if args.add is None and args.remove is None:
        return "No devices specified"

    insertions = [] if args.add is None else args.add
    removals = [] if args.remove is None else args.remove

    return rdfm.api.groups.assign_device(config,
                                         args.group_id,
                                         insertions,
                                         removals)


def set_target(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - setting a target version for the group

    Internally, this adds the `exact_match,...` policy to the group, but for
    simple use cases the user shouldn't need to mess with them manually.
    """
    policy = f"exact_match,{args.version}"
    return rdfm.api.groups.set_policy(config, args.group_id, policy)


def add_groups_parser(parser: argparse._SubParsersAction):
    """ Create a parser for the `groups` CLI command tree within
        the given subparser.

     Args:
        parser: subparser object created using `add_subparsers`
    """
    groups = parser.add_parser('groups', help='group management')
    sub = groups.add_subparsers(required=True, title='group commands')

    list = sub.add_parser('list', help='list all groups')
    list.set_defaults(func=list_groups)

    create = sub.add_parser('create', help='create a group')
    create.set_defaults(func=create_group)
    create.add_argument('--name', type=str, required=True,
                        help='name of the group')
    create.add_argument('--description', type=str, required=True,
                        help='group description')
    create.add_argument('--metadata', type=str, action='append',
                        help='append extra metadata to the group, specified as key=value pairs, can be provided multiple times')

    delete = sub.add_parser('delete', help='delete a group')
    delete.set_defaults(func=delete_group)
    delete.add_argument('--group-id', type=str, required=True,
                        help='group identifier')

    target = sub.add_parser('target-version', help='set the target version the group should be updated to')
    target.set_defaults(func=set_target)
    target.add_argument('--group-id', type=str, required=True,
                        help='group identifier')
    target.add_argument('--version', type=str, required=True,
                        help='version identifier')

    assign = sub.add_parser('assign-package', help='assign packages to a group')
    assign.set_defaults(func=assign_package)
    assign.add_argument('--group-id', type=str, required=True,
                        help='group identifier')
    assign.add_argument('--package-id', type=str, action='append',
                        help='package identifiers to assign, which will replace all previous assignments.'
                             ' Can be provided multiple times (or ignored entirely to clear all assignments)')

    modify = sub.add_parser('modify-devices', help='modify devices belonging to a group')
    modify.set_defaults(func=modify_devices)
    modify.add_argument('--group-id', type=str, required=True,
                        help='group identifier')
    modify.add_argument('--add', type=str, action='append',
                        help='device identifiers of devices to add to the group, can be provided multiple times')
    modify.add_argument('--remove', type=str, action='append',
                        help='device identifiers of devices to remove from the group, can be provided multiple times')
