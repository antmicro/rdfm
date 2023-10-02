from typing import Optional
import storage.local
import storage.s3
import configuration

def driver_by_name(name: str, config: configuration.ServerConfig) -> Optional[storage.local.LocalStorage]:
    """Gets a storage driver given by the name

       Storage drivers abstract away the file handling part of artifact storage.
       All storage drivers are expected to store their metadata inside a simple dictionary.
    """
    match name:
        case "local":
            return storage.local.LocalStorage(config)
        case "s3":
            return storage.s3.S3Storage(config)
        case _:
            return None
