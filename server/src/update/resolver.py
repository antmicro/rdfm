from typing import List, Optional, Type
import networkx as nx
from rdfm.schema.v1.updates import (
    META_SOFT_VER,
    META_DEVICE_TYPE,
    META_XDELTA_SUPPORT,
    META_RSYNC_SUPPORT,
)
from update.policies.base import BasePolicy


def requirements_satisfied(base: dict[str, str], update: dict[str, str]
                           ) -> bool:
    """
    Checks if package `base` satisfies the requirements imposed by package
    `update`, i.e if `update` can be installed on top of `base`.

    Returns:
        True, if package `base` satisfies all `requires:` clauses in package
        `update`; False otherwise
    """
    compatible = True
    for k, v in update.items():
        # Only check requirements
        if not k.startswith("requires:"):
            continue

        actual_key = k.removeprefix("requires:")
        if actual_key not in base:
            # Requirement from `update` is completely missing from `base`
            compatible = False
        elif base[actual_key] != v:
            # Requirement from `update` has a different value in `base`
            compatible = False

    # Some special handling is required for the software version
    # and device types.
    if base[META_SOFT_VER] == update[META_SOFT_VER]:
        compatible = False
    if base[META_DEVICE_TYPE] != update[META_DEVICE_TYPE]:
        compatible = False

    return compatible


class PackageResolver:
    device: dict[str, str]
    packages: List[dict[str, str]]
    policy: Type[BasePolicy]

    def __init__(
        self,
        device_meta: dict[str, str],
        packages: List[dict[str, str]],
        policy: Type[BasePolicy],
    ) -> None:
        """Initializes the package resolver

        Args:
            device_meta: current metadata reported by the device
            packages: list of assigned packages
            policy: policy object used for the group
        """
        self.device = device_meta
        self.packages = packages
        self.policy = policy

    def resolve(self) -> Optional[int]:
        """Attempt to resolve the path to the target software version specified
            in the policy via the available packages, and return the package
            that should be installed next.

        Returns:
            None, if no path is available or the device is already on the
            latest version int, index number of the next package that should be
            installed from the list provided in the resolver constructor
        """
        # Current running version
        current_version = self.device[META_SOFT_VER]
        # Target version, as indicated by the policy applied on the device
        target_version = self.policy.evaluate(self.device)
        if target_version is None:
            print(
                "Skipping update check for device with metadata:",
                self.device,
                ", as policy indicates no target version",
            )
            return None

        G = nx.MultiDiGraph()
        # Add node for the base version, i.e the device's currently
        # installed software
        G.add_node(
                current_version, subset=str(current_version), package="base")
        # Create initial nodes for all software versions reachable from the
        # available packages, we don't care about requirements at this stage
        # other than the package must be device-type compatible.
        for package_meta in self.packages:
            if package_meta[META_DEVICE_TYPE] != self.device[META_DEVICE_TYPE]:
                continue
            # There may be many packages with the same target software version
            if G.has_node(package_meta):
                continue

            ver = package_meta[META_SOFT_VER]
            G.add_node(ver, subset=str(ver), package=str(ver))

        # Sanity check - does the target version exist on the graph?
        # If not, there is nothing we can do.
        if not G.has_node(target_version):
            print(
                f"Package graph has no node with version '{target_version}'! \
                  Most likely no compatible packages were assigned to the \
                  device's group."
            )
            return None

        # First, resolve the packages that can be installed on top of the
        # currently running version. This is done by checking every single
        # package against the current device metadata and seeing if
        # any are compatible.
        # Packages may have `requires` clauses on keys that change their value
        # after an update, so only the edges coming from the current version
        # are guaranteed to be 100% compatible with the device.
        for idx, target in enumerate(self.packages):
            if not requirements_satisfied(self.device, target):
                continue

            cost = 1  # FIXME
            G.add_edge(
                current_version,
                target[META_SOFT_VER],
                package=idx,
                metadata=target,
                cost=cost,
            )

        # Next, resolve which packages can be installed on top of which other
        # packages.
        # This is done by checking every package against each other, which
        # makes this O(n^2) in the count of assigned packages.
        # This does not take into consideration local device metadata!
        # In very niche edge cases, these edges may not actually be compatible
        # with the device, but at no point will an incompatible package ever
        # be chosen as the next hop.
        for base in self.packages:
            for idx, target in enumerate(self.packages):
                if not requirements_satisfied(base, target):
                    continue

                cost = 1  # FIXME
                G.add_edge(
                    base[META_SOFT_VER],
                    target[META_SOFT_VER],
                    package=idx,
                    metadata=target,
                    cost=cost,
                )

        try:
            # Try finding the shortest installation path to the target
            sp = nx.shortest_path(
                G, source=current_version, target=target_version, weight="cost"
            )

            edge_path = []
            # Reconstruct the edges for the shortest path
            # NetworkX only returns the nodes of the shortest path
            for subpath in nx.utils.pairwise(sp):
                # `G.out_edges` ignores the destination, filter the edges that
                # don't lead to the correct node.
                valid_edges = list(
                    filter(
                        lambda edge: edge[1] == subpath[1],
                        G.out_edges(subpath, data=True),
                    )
                )
                _, _, minimal = min(valid_edges, key=lambda e: e[2]["cost"])
                edge_path.append(minimal["package"])

            return edge_path[0] if len(edge_path) > 0 else None
        except nx.NetworkXNoPath:
            print(
                f"No path to the policy-specified target version \
                '{target_version}' was found!"
            )
            return None
