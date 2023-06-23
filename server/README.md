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
