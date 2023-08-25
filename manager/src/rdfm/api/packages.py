import os
import datetime
import requests
import requests_toolbelt
import rdfm.config
from rdfm.api import wrap_api_error
from typing import List, Any, Optional, Callable
from types import SimpleNamespace
from marshmallow import Schema, fields, post_load


class Package():
    id: int
    created: datetime.datetime
    sha256: str
    driver: str
    metadata: dict[str, Any]

    def __init__(self, id, created, sha256, driver, metadata):
        self.id = id
        self.created = created
        self.sha256 = sha256
        self.driver = driver
        self.metadata = metadata


class PackageSchema(Schema):
    """ Package schema, as returned by the API
    """
    id = fields.Int(required=True)
    created = fields.DateTime(required=True, format="rfc")
    sha256 = fields.Str(required=True)
    driver = fields.Str(required=True)
    # FIXME: `values` should be fields.Str(), `Raw` is a workaround
    #        for the server returning non-string values
    metadata = fields.Dict(keys=fields.Str(),
                           values=fields.Raw(),
                           required=True)

    @post_load
    def make_package(self, data, **kwargs):
        return Package(**data)


def fetch_all(config: rdfm.config.Config) -> List[Package]:
    response = requests.get(rdfm.api.escape(config, "/api/v1/packages"),
                            cert=config.ca_cert,
                            auth=config.authorizer)
    if response.status_code != 200:
        raise RuntimeError(f"Server returned unexpected status code {response.status_code}")

    packages: List[Package] = PackageSchema(many=True).load(response.json())
    return packages


def upload(config: rdfm.config.Config,
           metadata: dict[str, Any],
           filepath: str,
           progress: Callable[[int, int], None]) -> Optional[str]:
    """ Upload a package to the server

    Args:
        metadata: dictionary containing metadata of the package
        filepath: path to the package file

    Returns:
        user-friendly error string if the process failed
    """
    # The server expects the package to be sent within the `file` key,
    # and a filename NEEDS to be attached for the server to recognize
    # the field as a valid file.
    fields = {
        "file": (os.path.basename(filepath), open(filepath, "rb"))
    }
    # The rest of the fields are used as metadata for the package
    # First argument of the tuple is the filename, which we do not
    # want to provide for metadata.
    for key in metadata:
        if key == "file":
            return "Metadata key 'file' is not valid"
        fields[key] = (None, metadata[key])

    encoder = requests_toolbelt.MultipartEncoder(fields=fields)
    monitor = requests_toolbelt.MultipartEncoderMonitor(encoder,
                                                        lambda monitor: progress(monitor.bytes_read, monitor.len))
    response = requests.post(rdfm.api.escape(config, "/api/v1/packages"),
                             cert=config.ca_cert,
                             auth=config.authorizer,
                             data=monitor,
                             headers={'Content-Type': monitor.content_type})
    return wrap_api_error(response, "Uploading package failed")


def delete(config: rdfm.config.Config, package_id: int) -> Optional[str]:
    """ Upload a package to the server

    Args:
        package_id: identifier of package to delete

    Returns:
        user-friendly error string if the process failed
    """
    response = requests.delete(rdfm.api.escape(config, f"/api/v1/packages/{package_id}"),
                               cert=config.ca_cert,
                               auth=config.authorizer)
    if response.status_code == 409:
        return "Deleting package failed: Package is assigned to at least one group and cannot be removed"
    return wrap_api_error(response, "Deleting package failed")
