# RDFM OTA Manual

This chapter contains key information about the RDFM OTA update system.

## Key concepts

Below is a brief explanation of the key entities of the RDFM update system.

### Devices

From the server's point of view, a device is any system that is running an RDFM-compatible update client.
For example, see [RDFM Linux Device Client](./rdfm_linux_device_client.md).
Each device actively reports its metadata to the server:
- Currently running software version (`rdfm.software.version`)
- Device type (`rdfm.hardware.devtype`)
- Other client-specific metadata

### Packages

A package is any file that can be used by a compatible update client to update the running system.
From the server's point of view, update packages are simple binary blobs and no specific structure is enforced.
Each package has metadata assigned to it that indicates its contents.
The following metadata fields are mandatory for all packages:
- Software version (`rdfm.software.version`) - indicates the version of the contained software
- Device type (`rdfm.hardware.devtype`) - indicates the device type a package is compatible with

The device type is used as the first filter when searching for a compatible update package.
Any package that does not match the device type reported by the update client will be considered incompatible.

A package may also contain metadata with `requires:` clauses.
The `requires` clause is used to indicate dependencies on certain metadata properties of the device.
In its most basic form, it can be used to indicate a dependency on a certain system image to be installed for proper delta update installation.
For more complex use cases involving many intermediate update steps, it can also be used to enforce an order in which certain packages must be installed.

### Groups

A group consists of many assigned devices. Each group can also be assigned one or many packages.
The group itself also contains metadata about the group name, description, update policy, and other arbitrary information which can be used by custom frontends interacting with the server.

### Update policy

An update policy defines the target version the devices within a given group will be updated to.
The policy is a string with the syntax `<policy>,[arguments]`.
Required arguments depend on the specific policy being used.
Currently, the following policies are supported:
- `no_update` (**default**) - requires no arguments, the server will treat all devices within the group as up-to-date, and will not return any packages to devices requesting an update check. **This is the default update policy for all newly created groups**.
- `exact_match` - specifies that the server will attempt to install the target software version on each of the devices in the group.
Example usage: `exact_match,version1` - this specifies that the server will attempt to bring all of the devices to the software version `version1`.
This process may involve installing many intermediate packages, but the end result is a device that's running the specified version.
The server will use group-assigned packages when resolving the dependency graph required for reaching the target version.

## Update resolution

When resolving a path to the correct target version, the server utilizes only the group-assigned packages.
When a device is requesting an update check, a package dependency graph is created.
The edges of the graph correspond to different packages available during the update process (which are compatible with the device, as indicated by the `rdfm.hardware.devtype` field), while the nodes indicate the software versions (as indicated by the `rdfm.software.version` fields of each package).
Next, the group's update policy is queried, which indicates the target version/node each device should be attempting to reach.
The shortest path between the currently running node and the target node is used as instructions for how the server should lead the device to the specified version.

## Example scenario: simple update assignment

Consider a group with the following packages assigned:
- P0 - `devtype=foo`, `version=v1`
- P1 - `devtype=bar`, `version=v2`
- P2 - `devtype=baz`, `version=v3`

The group is specified to update to version `v3` per the policy. Devices are reporting the following metadata:
- D0 - `devtype=foo`, `version=v3`
- D1 - `devtype=bar`, `version=v3`
- D2 - `devtype=baz`, `version=v3`

In this scenario, devices `D0` and `D1` shall receive the update packages `P0` and `P1` respectively.
The device `D2` is considered up-to-date, as its version matches the target specified in the group policy.

## Example scenario: downgrades

Consider a group with the following packages assigned:
- P0 - `devtype=foo`, `version=v4`

The group is specified to update to version `v4` per the policy. Devices are reporting the following metadata:
- D0 - `devtype=foo`, `version=v5`

In this scenario, the device `D0` will receive the package `P0` to be installed next.

## Example scenario: sequential updates

Consider a group with the following packages assigned:
- P0 - `devtype=foo`, `version=v2`, `requires:version=v1`
- P1 - `devtype=foo`, `version=v3`, `requires:version=v2`

The group is specified to update to version `v3` per the policy. Devices are reporting the following metadata:
- D0 - `devtype=foo`, `version=v1`

In this scenario, the device `D0` will first be updated to the package `P0`, as it's the only package that is compatible (matching device type and different version than the one running on the device).
The package's only `requires` clause also matches against the device's metadata.

After successful installation, during the next update check on the newly installed version (`v1`), the device will receive the next available package.
As the device is now reporting a version field of `v1` and the package's `requires:` clause passes, package `P1` becomes the next candidate package available for installation.
After successful instalation of `P1`, no more packages are available and the device is considered to be up-to-date.

## Example scenario: delta updatess

Consider a group with the following packages assigned:
- P0 (delta) - `devtype=foo`, `version=v5`, `rootfs=e6e2531..`, `requires:version=v0`, `requires:rootfs=2f646ac..`
- P1 (delta) - `devtype=foo`, `version=v5`, `rootfs=e6e2531..`, `requires:version=v2`, `requires:rootfs=6d9aee4..`

The group is specified to update to version `v5` per the policy. Devices are reporting the following metadata:
- D0 - `devtype=foo`, `version=v0`, `rootfs=2f646ac..`
- D1 - `devtype=foo`, `version=v2`, `rootfs=6d9aee4..`

In this scenario, devices `D0` and `D1` will receive packages `P0` and `P1` as updates respectively.
The packages themselves contain different binary contents, in this case a delta between a given base version's system partition (`v0` and `v2`) and the target (`v5`), but the end result is an identical system on both devices.
This way, many delta packages may be provided for updating a fleet consisting of a wide range of running versions.
