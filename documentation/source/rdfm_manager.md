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

available commands:
  {devices,packages,groups}
    devices             device management
    packages            package management
    groups              group management
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
