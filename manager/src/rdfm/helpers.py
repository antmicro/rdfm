from typing import Optional
import requests


def split_metadata(flags: list[str]) -> dict[str, str]:
    """ Split metadata flags into a dictionary

    This converts a list of strings in the form of `key=value` to
    a dictionary, with each `key` containing the specified `value`.

    Duplicate keys will be ignored - the first key in the list will
    be used.
    """
    metadata = {}
    if flags is None:
        return metadata
    # Split the metadata and construct a proper dictionary
    for pair in flags:
        key, value = pair.split('=', 1)
        if key in metadata:
            print(f"WARNING: duplicate metadata key: '{key}',"
                  "only the previously specified value "
                  f"will be used ('{metadata[key]}')")
            continue
        metadata[key] = value
    return metadata
