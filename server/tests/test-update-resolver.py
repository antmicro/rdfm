import pytest
from update.resolver import PackageResolver
from rdfm.schema.v1.updates import (
    META_SOFT_VER,
    META_DEVICE_TYPE,
    META_XDELTA_SUPPORT,
    META_RSYNC_SUPPORT,
)
from update.policies.exact_match import ExactMatch

XDELTA = {META_XDELTA_SUPPORT: "true"}
RSYNC = {META_RSYNC_SUPPORT: "true"}

def dummy_device(ver: str):
    """ Creates a dummy device metadata object
    """
    return {
        META_DEVICE_TYPE: "dummy",
        META_SOFT_VER: ver,
    }


def test_simple_resolve():
    """ Test with only one compatible package available

    Simplest possible update case - a single assigned package, with no requirements.
    """
    packages = [
        {
            META_SOFT_VER: "v1",
            META_DEVICE_TYPE: "dummy"
        }
    ]
    policy = ExactMatch("v1")
    resolver = PackageResolver(dummy_device("v0"), packages, policy)

    assert resolver.resolve() == 0, "update resolution should return index of the available update"


def test_simple_requirements():
    """ Test linear requirements resolution.

    Very simple test of package dependency resolution, with no special
    cases and a linear dependency graph:

        v0 --> v1 --> v2 --> v3 --> v4
    """
    packages = [
        {
            META_SOFT_VER: "v1",
            META_DEVICE_TYPE: "dummy",
        },
        {
            META_SOFT_VER: "v2",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_SOFT_VER}": "v1",
        },
        {
            META_SOFT_VER: "v3",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_SOFT_VER}": "v2",
        },
        {
            META_SOFT_VER: "v4",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_SOFT_VER}": "v3",
        }
    ]
    policy = ExactMatch("v4")

    # Test each update step
    # v0 -> v1
    assert PackageResolver(dummy_device("v0"), packages, policy).resolve() == 0, "next package to install should be v1"
    # v1 -> v2
    assert PackageResolver(dummy_device("v1"), packages, policy).resolve() == 1, "next package to install should be v2"
    # v2 -> v3
    assert PackageResolver(dummy_device("v2"), packages, policy).resolve() == 2, "next package to install should be v3"
    # v3 -> v4
    assert PackageResolver(dummy_device("v3"), packages, policy).resolve() == 3, "next package to install should be v4"
    # v4 -> no more updates
    assert PackageResolver(dummy_device("v4"), packages, policy).resolve() == None, "no more updates should be available"


def test_multiple_unbounded_packages():
    """ Test handling of multiple unrestricted packages (without any requirements).

    In this case, the package dependency graph will contain cycles, as follows:

    v0 ----> v1 <-.
     |            |
     `-----> v2 <-'

    The policy mechanism prevents the server from repeatedly forcing an install of
    the two only assigned packages (`v1` and `v2`) in a loop.
    """
    packages = [
        {
            META_SOFT_VER: "v1",
            META_DEVICE_TYPE: "dummy",
        },
        {
            META_SOFT_VER: "v2",
            META_DEVICE_TYPE: "dummy",
        },
    ]
    policy = ExactMatch("v2")
    assert PackageResolver(dummy_device("v0"), packages, policy).resolve() == 1, "next package to install should be v2"
    assert PackageResolver(dummy_device("v2"), packages, policy).resolve() == None, "no more updates should be available"


def test_multiple_version_paths():
    """ Test handling of alternative routes for reaching a version.

    Multiple packages may report the same software version, but have completely
    different contents. This is the case for delta updates, which will contain
    a different delta depending on the base version used for generating them.
    It is important to distinguish between packages and software versions;
    in the simplest case there will be a 1:1 mapping between them, however
    this will not always be the case.

    In this scenario, the package dependency graph may have alternative paths,
    all leading to the same software version:

           P0
    v0 ---------> v5
                  ^
                  |
          v2------'
               P1
    """
    packages = [
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_SOFT_VER}": "v0",
        },
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_SOFT_VER}": "v2",
        }
    ]
    policy = ExactMatch("v5")

    # Two different devices requesting an update check
    assert PackageResolver(dummy_device("v0"), packages, policy).resolve() == 0, "device should receive package P0"
    assert PackageResolver(dummy_device("v2"), packages, policy).resolve() == 1, "device should receive package P1"
    assert PackageResolver(dummy_device("v5"), packages, ExactMatch("v0")).resolve() == None, "should be impossible to resolve using these packages"


def test_ambiguous_packages():
    """ Test handling of package ambiguity.

    A device may have multiple ambiguous packages available for reaching
    a certain version. For example:

        P0
    v0 ----> v5
     |        ^
     |  P1    |
     `--------'

    An example scenario of this may be a fallback full package used to update
    a wider range of devices and a delta update provided for a subset of the
    fleet.
    """
    packages = [
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
        },
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_SOFT_VER}": "v0",
        }
    ]
    policy = ExactMatch("v5")

    assert PackageResolver(dummy_device("v0"), packages, policy).resolve() is not None, "device should receive any package"


def test_delta_algorithm_support():
    packages = [
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_RSYNC_SUPPORT}": "true",
            f"requires:{META_SOFT_VER}": "v0",
        },
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_XDELTA_SUPPORT}": "true",
            f"requires:{META_SOFT_VER}": "v0",
        },
    ]
    policy = ExactMatch("v5")

    # RSYNC-only device -> RSYNC delta (idx 0)
    assert PackageResolver(dummy_device("v0") | RSYNC, packages, policy).resolve() == 0

    # XDELTA-only device -> XDELTA delta (idx 1)
    assert PackageResolver(dummy_device("v0") | XDELTA, packages, policy).resolve() == 1


def test_device_without_delta_support():
    packages = [
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_RSYNC_SUPPORT}": "true",
            f"requires:{META_SOFT_VER}": "v0",
        },
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_XDELTA_SUPPORT}": "true",
            f"requires:{META_SOFT_VER}": "v0",
        },
    ]
    policy = ExactMatch("v5")

    # device without delta support -> no match
    assert PackageResolver(dummy_device("v0"), packages, policy).resolve() is None


def test_device_without_delta_support_full_update():
    packages = [
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_RSYNC_SUPPORT}": "true",
            f"requires:{META_SOFT_VER}": "v0",
        },
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_XDELTA_SUPPORT}": "true",
            f"requires:{META_SOFT_VER}": "v0",
        },
        {
            META_SOFT_VER: "v5",
            META_DEVICE_TYPE: "dummy",
            f"requires:{META_SOFT_VER}": "v0",
        },
    ]
    policy = ExactMatch("v5")

    # device without delta support -> full update (idx 2)
    assert PackageResolver(dummy_device("v0"), packages, policy).resolve() == 2
