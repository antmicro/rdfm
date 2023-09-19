from typing import Type
from update.policies.exact_match import ExactMatch
from update.policies.base import BasePolicy
from update.policies.no_update import NoUpdate


def create(policy_str: str) -> Type[BasePolicy]:
    """ Parses a given policy string and creates an associated policy object.
    """
    parts = policy_str.split(',', 1)
    if len(parts) != 2:
        raise RuntimeError("invalid policy string, missing arguments")

    policy = parts[0]
    args = parts[1]

    match policy:
        case "no_update":
            return NoUpdate(args)
        case "exact_match":
            return ExactMatch(args)
        case _:
            raise RuntimeError(f"invalid policy type: '{policy}'")
