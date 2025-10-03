# RDFM Manager utility

## Introduction

The RDFM Manager (`rdfm-mgmt`) utility allows authorized users to manage resources exposed by the RDFM Management Server.

## Installation

Before proceeding, make sure that you have installed Python (at least version 3.11) and the `pipx` utility:
- **Debian (Bookworm)** - run `sudo apt update && sudo apt install pipx`
- **Arch** - `sudo pacman -S python-pipx`

The prefered mode of installation for `rdfm-mgmt` is via `pipx`.
To install `rdfm-mgmt`, you must first clone the RDFM repository:

```
git clone https://github.com/antmicro/rdfm.git
cd rdfm/
```

Afterwards, run the following commands:

```
cd manager/
pipx install .
```

This will install the `rdfm-mgmt` utility and its dependencies for the current user within a virtual environment located at `/home/<user>/.local/pipx/venv`.
The `rdfm-mgmt` executable will be placed in `/home/<user>/.local/bin/` and should be immediately accessible from the shell.
Depending on the current system configuration, adding the above directory to the `PATH` may be required.

## Configuration

Additional RDFM Manager configuration is stored in the current user's `$HOME` directory, in the `$HOME/.config/rdfm-mgmt/config.json` file.
By default, RDFM Manager will add authentication data to all requests made to the RDFM server, which requires configuration of an authorization server and client credentials for use with the OAuth2 `Client Credentials` flow.
If authentication was disabled on the server-side, you can disable it in the manager as well by passing the `--no-api-auth` CLI flag like so:

```
rdfm-mgmt --no-api-auth groups list
```

An example configuration file is shown below.
In this case, the [Keycloak authorization server](https://www.keycloak.org/) was used:

```json
{
        "auth_url": "http://keycloak:8080/realms/master/protocol/openid-connect/token",
        "client_id": "rdfm-client",
        "client_secret": "RDSwDyUMOT7UXxMqMmq2Y4vQ1ezxqobi"
}
```

Explanation of each required configuration field is shown below:
- `auth_url` - URL to the authorization server's [token endpoint](https://swagger.io/docs/specification/authentication/openid-connect-discovery/)
- `client_id` - Client ID to use for authentication using OAuth2 Client Credentials flow
- `client_secret` - Client secret to use for authentication using OAuth2 Client Credentials flow

:::{note}
If you're also setting up the server, please note that the above client credentials are **NOT** the same as the server's Token Introspection credentials.
Each user of ``rdfm-mgmt`` should receive different credentials and be assigned scopes based on their allowed access level.
:::


## Building the wheel

For installation instructions, see the [Installation section](#installation).
Building the wheel is not required in this case.

To build the `rdfm-mgmt` wheel, you must have Python 3 installed, along with the `Poetry` dependency manager.

Building the wheel can be done as follows:

```
cd manager/
poetry build
```

## Usage

For more detailed information, see the help messages associated with each subcommand:

```
$ rdfm-mgmt -h
usage: rdfm-mgmt

RDFM Manager utility

options:
  -h, --help            show this help message and exit
  --url URL             URL to the RDFM Management Server (default: http://127.0.0.1:5000/)
  --cert CERT           path to the server CA certificate used for establishing an HTTPS connection (default: ./certs/CA.crt)
  --no-api-auth         disable OAuth2 authentication for API requests (default: False)

available commands:
  {devices,packages,groups,permissions}
    devices             device management
    packages            package management
    groups              group management
    permissions         permission management
```

### Listing available resources

Listing devices:

```
rdfm-mgmt devices list
```

Listing registration requests:

```
rdfm-mgmt devices pending
```


Listing packages:

```
rdfm-mgmt packages list
```

Listing groups:

```
rdfm-mgmt groups list
```

Listing permissions:

```
rdfm-mgmt permissions list [--user <user id>] [--resource <resource type>] [--resource-id <resource id>] [--permission <permission type>]
```

### Uploading packages

```
rdfm-mgmt packages upload \
    --path file.img \
    --version "v0" \
    --device "x86_64"
```

### Deleting packages

```
rdfm-mgmt packages delete --package-id <package>
```

### Creating groups

```
rdfm-mgmt groups create --name "Group #1" --description "A very long description of the group"
```

### Deleting groups

```
rdfm-mgmt groups delete --group-id <group>
```

### Assign package to a group

Assigning one package:

```
rdfm-mgmt groups assign-package --group-id <group> --package-id <package>
```

Assigning many packages:

```
rdfm-mgmt groups assign-package --group-id <group> --package-id <package1> --package-id <package2>
```

Clearing package assignments:

```
rdfm-mgmt groups assign-package --group-id <group>
```

### Assign devices to a group

Adding devices:

```
rdfm-mgmt groups modify-devices --group-id <group> --add <device>
```

Removing devices:

```
rdfm-mgmt groups modify-devices --group-id <group> --remove <device>
```

### Setting a group's target version

```
rdfm-mgmt groups target-version --group-id <group> --version <version-identifier>
```

### Authorizing a device

```
rdfm-mgmt devices auth <mac-address>
```

You can then select the registration for this device to authorize.

### Permissions

RDFM Manager utility provides permission commands that allow granting permissions to specific users and resources.
They operate on resource types, resource IDs, user IDs and permission types.

#### Resource types

There are three resource types: `group`, `package` and `device`.

#### Resource IDs

Resource ID is the ID of given resource and together with the resource type uniquely identifies such resource.
You can determine the resource ID using `rdfm-mgmt <resource type> list` command, using the RDFM frontend or through the server API.
In case of the devices you can also use device's MAC address or name in place of the ID.

#### User IDs

User ID uniquely identifies the user.

In Keycloak, the user ID can be determined by logging into administration console, selecting the realm corresponding to the RDFM system and selecting `Users` from the menu.
Then, you will see the list of users.
Clicking on any user will enter user's details page where user ID will be visible.

#### Permission types

There are four standard permission types: `read`, `create`, `update` and `delete`.
There is also an additional `shell` permission type that can only be assigned to devices.

#### Creating permissions

```
rdfm-mgmt permissions create <resource type> --id <resource ids> --user <user ids> --permission <permission types>
```

For example, you can assign `read` permission to the user with ID `eed3d12d-e13b-4c4a-aebd-38b4d55c8947` for the group with ID `1` by invoking:

```
rdfm-mgmt permissions create group --id 1 --user eed3d12d-e13b-4c4a-aebd-38b4d55c8947 --permission read
```

You can assign permissions to multiple resources and users at once.
For example, the following command will assign `read` and `update` permissions to users `eed3d12d-e13b-4c4a-aebd-38b4d55c8947` and `eed3d12d-e13b-4c4a-aebd-38b4d55c8948` for devices with IDs `1` and `2`:

```
rdfm-mgmt permissions create device --id 1 2 --user eed3d12d-e13b-4c4a-aebd-38b4d55c8947 eed3d12d-e13b-4c4a-aebd-38b4d55c8948 --permission read update
```

The `shell` permission can only be assigned to devices:

```
rdfm-mgmt permissions create device --id 1 2 --user eed3d12d-e13b-4c4a-aebd-38b4d55c8947 eed3d12d-e13b-4c4a-aebd-38b4d55c8948 --permission shell
```

#### Deleting permissions

```
rdfm-mgmt permissions create <resource type> --id <resource ids> --user <user ids> --permission <permission types>
```

For example, you can revoke `read` permission from the user with ID `eed3d12d-e13b-4c4a-aebd-38b4d55c8947` for the group with ID `1` by invoking:

```
rdfm-mgmt permissions delete group --id 1 --user eed3d12d-e13b-4c4a-aebd-38b4d55c8947 --permission read
```

You can revoke permissions to multiple resources and users at once. For example, the following command will revoke `read`, `update`, and `shell` permissions from users `eed3d12d-e13b-4c4a-aebd-38b4d55c8947` and `eed3d12d-e13b-4c4a-aebd-38b4d55c8948` for devices with IDs `1` and `2`:

```
rdfm-mgmt permissions delete device --id 1 2 --user eed3d12d-e13b-4c4a-aebd-38b4d55c8947 eed3d12d-e13b-4c4a-aebd-38b4d55c8948 --permission read update shell
```

You can also revoke permissions for all resource IDs from given user using `--all-ids` flag.
For example, the following command will revoke read permission for all devices from user `eed3d12d-e13b-4c4a-aebd-38b4d55c8947`:

```
rdfm-mgmt permissions delete device --all-ids --user eed3d12d-e13b-4c4a-aebd-38b4d55c8947 --permission read
```
