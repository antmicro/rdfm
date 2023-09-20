from typing import Optional
import argparse
import rdfm.api.packages
import rdfm.config
import rdfm.helpers
import progressbar
import os.path
from rdfm.schema.v1.updates import META_SOFT_VER, META_DEVICE_TYPE


def list_packages(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - listing all packages
    """
    packages = rdfm.api.packages.fetch_all(config)

    print("Available packages:")
    for pkg in packages:
        print(f"Package ID: #{pkg.id}")
        print(f"\tUploaded on: {pkg.created}")
        print(f"\tSHA-256: {pkg.sha256}")
        print(f"\tStorage driver: {pkg.driver}")
        print("\tMetadata:")
        for k, v in pkg.metadata.items():
            print(f"\t\t{k}: {v}")
        print()
    return None


def callback_upload_progress_bar(sent: int,
                                 total: int,
                                 bar: progressbar.ProgressBar):
    """ Wrapper for printing the progress bar on package upload

    Args:
        sent: bytes sent so far
        total: total bytes to transfer
        bar: ProgressBar object
    """
    # Max value is set to unknown by default, but updated
    # after the first callback call
    bar.max_value = total
    bar.update(sent)


def upload_package(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - uploading a package
    """
    filepath = args.path
    if not os.path.isfile(filepath):
        return f"Uploading package failed: File {filepath} does not exist"

    version = args.version
    device = args.device
    metadata = {} if args.metadata is None else rdfm.helpers.split_metadata([ x for x in args.metadata])
    metadata[META_SOFT_VER] = version
    metadata[META_DEVICE_TYPE] = device

    # Setup the progress bar
    widgets = [
        filepath,
        ' ', progressbar.Percentage(),
        ' ', progressbar.Bar(marker='=', left='[', right=']'),
        ' ', progressbar.DataSize(),
        ' ', progressbar.FileTransferSpeed(),
        ' ', progressbar.ETA(),
    ]
    bar = progressbar.ProgressBar(max_value=progressbar.UnknownLength, widgets=widgets)
    progress_callback = lambda sent, total: callback_upload_progress_bar(sent, total, bar)

    error = rdfm.api.packages.upload(config, metadata, filepath, progress_callback)
    bar.finish()

    if error is None:
        print("Package uploaded")
    return error


def delete_package(config: rdfm.config.Config, args) -> Optional[str]:
    """ CLI entrypoint - deleting a package
    """
    print(f"Deleting package #{args.package_id}")
    return rdfm.api.packages.delete(config, args.package_id)


def add_packages_parser(parser: argparse._SubParsersAction):
    """ Create a parser for the `packages` CLI command tree within
        the given subparser.

     Args:
        parser: subparser object created using `add_subparsers`
    """
    packages = parser.add_parser('packages', help='package management')
    sub = packages.add_subparsers(required=True, title='package commands')

    list = sub.add_parser('list', help='list all uploaded packages')
    list.set_defaults(func=list_packages)

    upload = sub.add_parser('upload', help='upload a package')
    upload.set_defaults(func=upload_package)
    upload.add_argument('--path', type=str, required=True,
                        help='path to an update package file')
    upload.add_argument('--version', type=str, required=True,
                        help='software version of the uploaded package')
    upload.add_argument('--device', type=str, required=True,
                        help='device type compatible with the uploaded package')
    upload.add_argument('--metadata', type=str, action='append',
                        help='append extra metadata to the package, specified as key=value pairs')

    delete = sub.add_parser('delete', help='delete a package from the server')
    delete.set_defaults(func=delete_package)
    delete.add_argument('--package-id', type=str, required=True,
                        help='package identifier')
