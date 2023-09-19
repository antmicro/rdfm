from typing import Optional
from update.policies.base import BasePolicy


class NoUpdate(BasePolicy):
    """ No update policy - do not update any devices

    This policy requires no arguments and is the default for newly created
    groups. The server will not update any devices belonging to the group
    that has this policy.
    """

    def __init__(self, args) -> None:
        pass

    def evaluate(self, metadata: dict[str, str]) -> Optional[str]:
        return None
