# Usage

Each user and device client is a separate process.

## Prerequisites
Server and user client require `python3`. Devices require Linux. \
For device building and schema generation `rust` toolchain is is required. \
For certificate generation you can use `openssl`.

Install `python3` requirements: \
``pip install -r requirements.txt``

## Building device

```
cd device
cargo build
```

Compiled client can be found at: `device/target/debug/rdfm--device-client`

To build device schemas run use `rdfm-schema-generator`

## Encrypting communication

To use encrypted communication between all parties generate certificates.
To generate samples you can use `certgen.sh` script available
for testing purposes.

You can turn off encrypted communication with server and client
by using `no_ssl` argument.

## Running a server

```
python3 server.py
```

## Running a client

Register a user:

```
python3 client.py username
```

Register a device:

- using binary

```
./rdfm-device-client --name "devicename"
```

- using `cargo` (inside `device` directory):

```
cargo run --bin rdfm-device-client -- --name "devicename"
```

to include metadata provide file in argument `--file-metadata`

Client names should not contain whitespaces.

## Using a connected client

List devices:

```
LIST
```

Fetch information about device:

```
REQ devicename info
```

Requesting device to upload new metadata:

```
REQ devicename update
```

Send **proxy** request to a device:

```
REQ devicename proxy
```

**Connecting to the device**:

If proxy request was succesful, a message with port to connect to will be sent
to the user. 
To connect just use ``netcat`` (or similiar program)

```
nc IP_ADDR PORT
```

Exit client:

```
exit
```
