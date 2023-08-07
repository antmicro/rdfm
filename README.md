# RDFM: over-the-air updater for embedded devices

Copyright (c) 2023 [Antmicro](https://www.antmicro.com)

Open source Over-the-Air (OTA) software updater and manager for embedded devices.

## Description

This repository contains sources for the RDFM OTA update system for embedded devices. It is structured as follows:

- `devices/` - contains RDFM-compatible clients that handle communication with the RDFM management server and perform the actual update procedure
- `server/` - contains the RDFM management server that distributes packages to connected devices
- `manager/` - contains the CLI tool used for managing devices connected to the server
- `tools/` - contains tools used by RDFM components
- `common/` - contains common libraries used by RDFM components

For more details, see the individual README files in the above directories.

## License

`RDFM` is licensed under the Apache-2.0 license. For details, see the [LICENSE](LICENSE) file.
