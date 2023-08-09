# RDFM Management Server

## Introduction

The RDFM Management Server is a core part of the RDFM ecosystem. The server manages incoming device connections and grants authorization only to those which are allowed to check-in with the server.
It also handles package upload and management, deploy group management and other crucial functionality required for robust and secure device Over-The-Air (OTA) updates along with allowing remote system management without exposing devices to the outside world.

## Database backend

Currently, to simplify development, the RDFM Management Server utilizes SQLite for storing server data. The database is stored in the `devices.db` file. This will be expanded in the future to allow using the typical DBMS backends instead.

## Storage backend

Uploading packages is done by utilizing a storage backend. In the near future, more backends will be added that will allow storing packages in configurable bucket storage (such as S3 or GCP). For development purposes, a local storage backend is available that stores all uploaded packages to a temporary file under `/tmp/.rdfm-local-storage/` folder.

## REST API

The server exposes a management and device API that is used by management software and end devices. A comprehensive list of all API endpoints is available in the [RDFM Server API Reference chapter](api.rst).

## Building

To build the server, you must have Python 3 installed, along with the `Poetry` dependency manager.

Building the wheel can be done as follows:

```
cd server/
poetry build
```

## Setting up a development environment

This section pertains only to the development setup. **This should not be used for production deployments!**

The server utilizes the Poetry tool to manage project dependencies.
You can run a development RDFM Management Server by running the following commands:

```bash
cd server/
export JWT_SECRET="THISISATESTDEVELOPMENTSECRET123"
poetry build && poetry install && poetry run python -m rdfm_mgmt_server -no_ssl
```

This launches the RDFM Management Server with no encryption, listening on `localhost`/`127.0.0.1`. By default, the device communication socket is listening on port `1234`, while the HTTP API is exposed on port `5000`.

