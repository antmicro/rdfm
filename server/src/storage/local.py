import uuid
import os
import hashlib
import shutil
import configuration
import urllib.parse

"""Local storage driver, used for debugging purposes
"""

class LocalStorage():
    config: configuration.ServerConfig

    def __init__(self, config: configuration.ServerConfig) -> None:
        self.config = config


    """Updates the contents of the specified package
       This method has upsert semantics - if the specified package does not exist,
       it is created. Otherwise, contents of the package are modified.
       The metadata of the package is updated. All storage drivers shall use:
            rdfm.storage.<storage-driver-name>.<key>
       metadata keys.
    """
    def upsert(self, metadata: dict[str, str], package_path: str) -> bool:
        # Create the storage directory if it does not exist
        if not os.path.isdir(self.config.package_dir):
            os.mkdir(self.config.package_dir)
        print("Local storage update package:", metadata, "path:", package_path)
        store_name = str(uuid.uuid4())
        destination_path = os.path.join(self.config.package_dir, store_name)
        shutil.copy(package_path, destination_path)

        metadata["rdfm.storage.local.uuid"] = store_name
        metadata["rdfm.storage.local.length"] = os.path.getsize(destination_path)
        return True


    """Makes a direct HTTP URL to the specified package with given expiration time
       Expiration is in seconds.
    """
    def generate_url(self, metadata: dict[str, str], expiry: int) -> str:
        schema = "http"
        port = self.config.http_port
        if self.config.encrypted:
            schema = "https"
        hostname = self.config.hostname
        path = f"/local_storage/{metadata['rdfm.storage.local.uuid']}"
        # Expiration time ignored, as local storage is just for debugging
        return urllib.parse.urljoin(f"{schema}://{hostname}:{port}",
                                    path)


    """Deletes the specified package from storage
    """
    def delete(self, metadata: dict[str, str]):
        name = metadata["rdfm.storage.local.uuid"]
        os.remove(os.path.join(self.config.package_dir, name))

