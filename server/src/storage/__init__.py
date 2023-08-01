from typing import Optional
import storage.local

def driver_by_name(name: str) -> Optional[storage.local.LocalStorage]:
    """Gets a storage driver given by the name

       Storage drivers abstract away the file handling part of artifact storage.
       All storage drivers are expected to store their metadata inside a simple dictionary.
    """
    match name:
        case "local":
            return storage.local.LocalStorage()
        case _:
            return None
