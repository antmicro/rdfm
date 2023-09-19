from typing import Optional
from update.policies.base import BasePolicy


class ExactMatch(BasePolicy):
    """ Exact match policy - always update to the specified software version

    This policy takes in a single argument: the software version to be used
    as a target when running the software update logic.
    As a result, the server will attempt to update every device within the
    group to the specified version.
    """
    version: str

    def __init__(self, args) -> None:
        self.version = args

    def evaluate(self, metadata: dict[str, str]) -> Optional[str]:
        return self.version
