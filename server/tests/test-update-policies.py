import update.policy
from update.policies.exact_match import ExactMatch
import pytest


def test_invalid():
    with pytest.raises(RuntimeError, match="missing arguments"):
        update.policy.create("invalid_policy")


def test_exact_match():
    policy = update.policy.create("exact_match,v0")
    assert isinstance(policy, ExactMatch), "parsed policy is an instance of ExactMatch"
    assert policy.version == "v0", "version was parsed correctly"

    dummy = {
        "rdfm.software.version": "v1",
        "rdfm.hardware.devtype": "dummy"
    }
    assert policy.evaluate(dummy) == "v0", "evaluating the policy returns the specified version"
