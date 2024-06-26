import datetime
from dateutil import tz
import ssl


def split_metadata(flags: list[str]) -> dict[str, str]:
    """Split metadata flags into a dictionary

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
        key, value = pair.split("=", 1)
        if key in metadata:
            print(
                f"WARNING: duplicate metadata key: '{key}',"
                "only the previously specified value "
                f"will be used ('{metadata[key]}')"
            )
            continue
        metadata[key] = value
    return metadata


def utc_to_local(utc: datetime.datetime) -> datetime.datetime:
    """Convert the given naive datetime UTC object to local timezone

    The server returns all datetime values implicitly in UTC. This is
    a helper to convert the UTC datetime to local for user display.
    """
    if utc is None:
        return None
    # Apply timezone information for UTC to the datetime
    utc = utc.replace(tzinfo=datetime.UTC)
    # Convert to the target timezone
    local_tz = tz.tzlocal()
    return utc.astimezone(local_tz)


def replace_http_schema_with_ws(server_url: str):
    """Replaces HTTP schema from the given URL with a WebSocket schema"""
    return server_url.replace("http://", "ws://").replace("https://", "wss://")


def make_ssl_context_from_cert_file(ca_cert: str) -> ssl.SSLContext:
    """Create an SSLContext for connecting to the server

    This is used when a custom validation certificate is passed to
    validate the connection to the server.
    """
    context = ssl.SSLContext()
    try:
        context.load_verify_locations(cafile=ca_cert)
    except Exception as e:
        raise RuntimeError(f"Failed to load CA chain from file: {e}")
    return context
