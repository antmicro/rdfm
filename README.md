RDFM: over-the-air updater for embedded Linux devices
==============================================

RDFM is an open source over-the-air (OTA) software updater for embedded Linux
devices.

See https://github.com/antmicro/tegra-demo-distro-with-rdfm for an example usage.

This repo contains sources for the `rdfm` command-line tool, which is used for installing artifacts on the device.
See `rdfm --help` for example usage.

Basic use is `rdfm install https://your-server.example/some/artifact.rdfm`.

Note: this software is based on the Mender OTA update system, but is not affiliated with it in any way.
