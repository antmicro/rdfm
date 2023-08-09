# RDFM Manager utility

## Introduction

The RDFM Manager (`rdfm-mgmt`) utility allows authorized users to manage resources exposed by the RDFM Management Server.

## Building

To build `rdfm-mgmt`, you must have Python 3 installed, along with the `Poetry` dependency manager.

Building the wheel can be done as follows:

```
cd manager/
poetry build
```

## Running

To run the `rdfm-mgmt` utility, run the following commands:

```
cd manager/
poetry build
poetry install
poetry run python -m rdfm_mgmt_client username
```

## Encrypting communication

To use encrypted communication between all parties you must generate proper certificates. For development purposes, refer to the `server/tests/certgen.sh` script as an example of certificate generation.

You can turn off encrypted communication between the server and client by passing the `no_ssl` argument to **both parties**.

## Usage

List connected devices:

```
LIST
```

Fetch information about device:

```
REQ device_name info
```

Request a device to upload new metadata:

```
REQ device_name update
```

Request a **proxy** connection with a device:

```
REQ device_name proxy
```

**File transfer**:

Upload file to device:

```
REQ device_name upload file_path src_file_path
```

Where `file_path` indicates the path on the device, `src_file_path` indicates the file to upload.

Download file from device:

```
REQ device_name download file_path
```

**Connecting to the device**:

If the proxy request was succesful, a message with port to connect to will be sent
to the user.
To connect just use these (or similiar) programs:

**Encrypted:**

```openssl s_client -CAfile certs/CA.crt -quiet -connect SERVER_ADDR:PORT```

**Not encrypted:**

```nc SERVER_ADDR PORT```

Exit client:

```
exit
```
