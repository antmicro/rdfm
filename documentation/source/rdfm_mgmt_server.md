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

When server is in debug mode (`app.run(debug=True, ...)` is set) every HTTP request received and response to it are printed to STDOUT.

## Setting up a Dockerized development environment

The RDFM server can also be deployed using a Docker container.
A `Dockerfile` is provided in the `server/deploy/` directory that builds a container suitable for running the server.
To manually build the container image, run the following from the **RDFM repository root** folder:

```bash
docker build -f server/deploy/Dockerfile -t antmicro/rdfm-server:latest .
```

A simple `docker-compose` file that can be used to run the server is provided below, and in the `server/deploy/docker-compose.development.yml` file.

```yaml
services:
  rdfm-server:
    image: antmicro/rdfm-server:latest
    restart: unless-stopped
    environment:
      - RDFM_JWT_SECRET=<REPLACE_WITH_CUSTOM_JWT_SECRET>
      - RDFM_DB_CONNSTRING=sqlite:////database/development.db
      - RDFM_HOSTNAME=rdfm-server
      - RDFM_API_PORT=5000
      - RDFM_DEVICE_PORT=1234
      - RDFM_DISABLE_ENCRYPTION=1
    ports:
      - "1234:1234"
      - "5000:5000"
    volumes:
      - db:/database/

volumes:
  db:
```

The server can then be started using the following command:

```bash
docker-compose -f server/deploy/docker-compose.development.yml up
```

Configuration of the RDFM server can be changed by using the following environment variables:

- `RDFM_JWT_SECRET` - secret key used by the server when issuing JWT tokens, this value must be kept secret and not easily guessable (for example, a random hexadecimal string).
- `RDFM_HOSTNAME` - hostname/IP address to listen on, when running the server in a container use the service name here (using above example, `rdfm-server`).
- `RDFM_API_PORT` - HTTP API port
- `RDFM_DEVICE_PORT` - device-server protocol port
- `RDFM_DB_CONNSTRING` - database connection string, for examples please refer to: [SQLAlchemy - Backend-specific URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls). Currently, only the SQLite and PostgreSQL engines were verified to work with RDFM (however: the PostgreSQL engine requires adding additional dependencies which are currently not part of the default server image, this may change in the future).
- `RDFM_DISABLE_ENCRYPTION` - disables encryption of device-server protocol data and usage of HTTPS in the API routes
- `RDFM_SERVER_CERT` - when using encryption, path to the server's certificate. The certificate can be stored on a Docker volume mounted to the container. For reference on generating the certificate/key pairs, see the `server/tests/certgen.sh` script.
- `RDFM_SERVER_KEY` - when using encryption, path to the server's private key. Additionally, the above also applies here.
