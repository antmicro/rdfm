from typing import Optional


class BasePolicy():
    def __init__(self, args) -> None:
        pass

    def evaluate(self, metadata: dict[str, str]) -> Optional[str]:
        """ Evaluate the result of applying the given policy
            on a specified device

        Args:
            metadata: device metadata

        Returns:
            None, if the policy indicates no specific version for this device
            str, policy-specified software version the device should target
        """
        return None
