# Remote Device Fleet Manager - RDFM

Copyright (c) 2023 [Antmicro](https://www.antmicro.com)

Remote Device Fleet Manager (RDFM) is an open source Over-the-Air (OTA) software updater and fleet manager for embedded devices.

## Description

This repository contains sources for the RDFM OTA update / fleet manager system.
It is structured as follows:

- `documentation/` - sources for the RDFM documentation
- `devices/` - RDFM-compatible clients that handle communication with the RDFM management server and perform the actual update procedure
- `server/` - RDFM management server that distributes packages to connected devices
- `manager/` - CLI tool used for managing devices connected to the server
- `tools/` - tools used by RDFM components
- `common/` - common libraries used by RDFM components

For more details, see the individual README files in the above directories and the [RDFM documentation](https://antmicro.github.io/rdfm) pages.

## License

`RDFM` is licensed under the Apache-2.0 license. For details, see the [LICENSE](LICENSE) file.
