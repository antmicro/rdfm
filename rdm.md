# rdfm-mgmt-shell

Prototype of the management panel server for IoT devices management.

This will enable easy management of many devices connected via network
to the server, without exposing themselves to the world.

### Prerequisites
Server and user client require `python3`.

Python programs use `poetry` build backend.

Device client building requires `Rust` toolchain.

All programs tested only on Linux.

### Usage
Each user and device client is a separate process.

### Installation

#### Device client
Run `cargo build` in `device` directory.

Built device client is located in `target/debug/rdfm_mgmt_device`

To generate device requests run `rdfm_schema_generator` binary.

#### Server
Run `python3 -m build` in `server` directory.

To install a module run `pip install .`.

#### User client
Run `python3 -m build` in `client` directory.

To install a module run `pip install .`.

### Running a server

```python -m rdfm_mgmt_server```

### Running a client
Register a user:

```python -m rdfm_mgmt_client username```

Register a device:

```rdfm_mgmt_device --name "devicename"```

or (in `device` directory)

```cargo run --bin rdfm_mgmt_device -- --name "devicename"```

Note that client names should not contain whitespaces.

To provide metadata add `--file-metadata` argument with metadata path.

### Using a connected client
List devices:

```LIST```

Send proxy request to a device:

```REQ device_name proxy```

Getting device information:

```REQ device_name info```

Requesting updating device information:

```REQ device_name update```

Upload file to device:

```REQ device_name upload file_path src_file_path```

Where `file_path` indicates path on device, `src_file_path` indicates of file to upload.

Download file from device:

```REQ device_name download file_path```

Connecting to the device:

If proxy request was succesful, a message with port to connect to will be sent to the user. \
To connect just use these (or similiar) programs:

**Encrypted:**

```nc SERVER_ADDR PORT```

**Not encrypted:**

```openssl s_client -quiet -connect SERVER_ADDR:PORT```

## TODO:
*General:*
- [x] Mypy type hints
- [x] Basic testing
- [x] IO prettyprinting
- [x] Docs
- [ ] Error handling
- [x] Some argument providing and "help" description
- [x] Requirements autoinstall script
- [x] Encrypted proxy shell
- [ ] File upload/download and exec functions
- [ ] Generate schema from user-side API (code -> schema)

*Server:*
- [x] collecting devices and users connected to them and forwarding info to selected clients
- [ ] structured and easily extendable status/misc info gatherer from devices
- [x] creating 1-1 user-device "proxy" connection for data transfer
- [x] simple authorization method for users
- [x] some kind of reverse tunnel to provide services such as SSH or telnet from devices to users without revealing a port to the world
- [x] HTTP REST requests in user-side

*Clients:*
- [x] connecting to the server and providing basic information about yourself (if you're a device, your name, address and port - these are provided in the socket connection, etc.)
- [x] forwarding requests to the server
- [x] receiving replies and deducing next steps depending on it
- [x] additional interface for controlling "proxy" user -> device communication
(just a shell through netcat for now)
- [x] binding services to the server port
- [x] compiled, light version for more demanding devices
- [x] HTTP REST requests in user-side