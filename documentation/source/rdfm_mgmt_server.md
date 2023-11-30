# RDFM Management Server

## Introduction

The RDFM Management Server is a core part of the RDFM ecosystem. The server manages incoming device connections and grants authorization only to those which are allowed to check-in with the server.
It also handles package upload and management, deploy group management and other crucial functionality required for robust and secure device Over-The-Air (OTA) updates along with allowing remote system management without exposing devices to the outside world.

## Database backend

Currently, to simplify development, the RDFM Management Server utilizes SQLite for storing server data. The database is stored in the `devices.db` file. This will be expanded in the future to allow using the typical DBMS backends instead.

## REST API

The server exposes a management and device API that is used by management software and end devices. A comprehensive list of all API endpoints is available in the [RDFM Server API Reference chapter](api.rst).

## Building

Note: It is recommended to use the [Dockerized development environment](#setting-up-a-dockerized-development-environment), to ensure the correct Python version is installed. The server requires a relatively modern version of Python, which may not be readily available on all distributions.

To build the server, you must have Python 3.11 installed, along with the `Poetry` dependency manager.

First, clone the RDFM repository:

```
git clone https://github.com/antmicro/rdfm.git
cd rdfm/
```

Next, building the wheel can be done as follows:

```
cd server/
poetry build
```

## Setting up a development environment

This section pertains only to the development setup. **This should not be used for production deployments!**
For this section, it is assumed that you have cloned the RDFM repository already.

The server utilizes the Poetry tool to manage project dependencies.
You can run a development RDFM Management Server by running the following commands:

```bash
cd server/
export JWT_SECRET="THISISATESTDEVELOPMENTSECRET123"
poetry build && poetry install && poetry run python -m rdfm_mgmt_server --no-ssl --no-api-auth --local-package-dir ./packages/
```

This launches the RDFM Management Server with no encryption, listening on `localhost`/`127.0.0.1`. By default, the device communication socket is listening on port `1234`, while the HTTP API is exposed on port `5000`.

When server is in debug mode (`app.run(debug=True, ...)` is set) every HTTP request received and response to it are printed to STDOUT.

## Setting up a Dockerized development environment

For this section, it is assumed that you have cloned the RDFM repository already.

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
      - RDFM_DISABLE_ENCRYPTION=1
      - RDFM_DISABLE_API_AUTH=1
      - RDFM_LOCAL_PACKAGE_DIR=/packages/
    ports:
      - "5000:5000"
    volumes:
      - db:/database/
      - pkgs:/packages/

volumes:
  db:
  pkgs:
```

The server can then be started using the following command:

```bash
docker-compose -f server/deploy/docker-compose.development.yml up
```

Configuration of the RDFM server can be changed by using the following environment variables:

- `RDFM_JWT_SECRET` - secret key used by the server when issuing JWT tokens, this value must be kept secret and not easily guessable (for example, a random hexadecimal string).
- `RDFM_HOSTNAME` - hostname/IP address to listen on, when running the server in a container use the service name here (using above example, `rdfm-server`).
- `RDFM_API_PORT` - HTTP API port
- `RDFM_DB_CONNSTRING` - database connection string, for examples please refer to: [SQLAlchemy - Backend-specific URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls). Currently, only the SQLite and PostgreSQL engines were verified to work with RDFM (however: the PostgreSQL engine requires adding additional dependencies which are currently not part of the default server image, this may change in the future).
- `RDFM_DISABLE_ENCRYPTION` - disables encryption of device-server protocol data and usage of HTTPS in the API routes
- `RDFM_SERVER_CERT` - when using encryption, path to the server's certificate. The certificate can be stored on a Docker volume mounted to the container. For reference on generating the certificate/key pairs, see the `server/tests/certgen.sh` script.
- `RDFM_SERVER_KEY` - when using encryption, path to the server's private key. Additionally, the above also applies here.
- `RDFM_LOCAL_PACKAGE_DIR` - specifies a path (local for the server) to a directory where the packages are stored
- `RDFM_STORAGE_DRIVER` - storage driver to use for storing artifacts. Accepted values: `local` (default), `s3`.
- `RDFM_DISABLE_API_AUTH` - disables request authentication on the exposed API routes. **WARNING: This is a development flag only! Do not use in production!** This causes all API methods to be freely accessible, without any access control in place!
- `RDFM_OAUTH_URL` - specifies the URL to an authorization server endpoint compatible with the RFC 7662 OAuth2 Token Introspection extension. This endpoint is used to authorize access to the RDFM server based on tokens provided in requests made by API users.
- `RDFM_OAUTH_CLIENT_ID` - if the authorization server endpoint provided in `RDFM_OAUTH_URL` requires the RDFM server to authenticate, this variable defines the OAuth2 `client_id` used for authentication.
- `RDFM_OAUTH_CLIENT_SEC` -  if the authorization server endpoint provided in `RDFM_OAUTH_URL` requires the RDFM server to authenticate, this variable defines the OAuth2 `client_secret` used for authentication.

## Configuring package storage location

### Storing packages locally

By default (when not using one of the above deployment setups), the server stores all uploaded packages to a temporary folder under `/tmp/.rdfm-local-storage/`.
To persist package data, configuration of an upload folder is required.
This can be done by using the `RDFM_LOCAL_PACKAGE_DIR` environment variable (in the Dockerized deployment), which should contain a path to the desired upload folder.

:::{warning}
This storage method should NOT be used for production deployments!
The performance of the built-in file server is severely limited and provides NO caching, which will negatively affect the update speed for all devices even when a few of them try downloading an update package at the same time.
It is recommended to use a dedicated storage solution such as S3 to store packages.
:::

### Storing packages on S3-compatible storage

The RDFM server can also store package data on S3 and other S3 API-compatible object storage servers.
The following environment variables allow changing the configuration of the S3 integration:
- `RDFM_S3_BUCKET` - name of the bucket to upload the packages to
- `RDFM_S3_ACCESS_KEY_ID` - Access Key ID to access the specified bucket
- `RDFM_S3_ACCESS_SECRET_KEY` - Secret Access Key to access the specified bucket
Additionally, when using S3 storage, the environment variable `RDFM_STORAGE_DRIVER` must be set to `s3`.

An example reference setup utilizing the MinIO Object Storage server is provided in the `server/deploy/docker-compose.minio.yml` file.
To run it, first build the RDFM server container like in the above setup guides:

```bash
docker build -f server/deploy/Dockerfile -t antmicro/rdfm-server:latest .
```

Then, run the following:

```
docker-compose -f server/deploy/docker-compose.minio.yml up
```

## Configuring API authentication

### Basic configuration

The above development setup does not provide any authentication for the RDFM API.
This is helpful for development or debugging purposes, however **under no circumstance should this be used in production deployments, as it exposes the entire API with no restrictions in place**.

By default, the RDFM server requires configuration of an external authorization server to handle token creation and scope management.
To be compatible with RDFM Management Server, the authentication server **MUST** support the OAuth2 Token Introspection extension ([RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662)).

The authorization server is configured using the following environment variables:
- `RDFM_OAUTH_URL` - specifies the URL to the Token Introspection endpoint of the authorization server.
- `RDFM_OAUTH_CLIENT_ID` - specifies the client identifier to use for authenticating the RDFM server to the authorization server.
- `RDFM_OAUTH_CLIENT_SEC` - specifies the client secret to use for authenticating the RDFM server to the authorization server.

For accessing the management API, the RDFM server does not issue any tokens itself.
This task is delegated to the authorization server that is used in conjunction with RDFM.
The following scopes are used for controlling access to different methods of the RDFM API:
- `rdfm_admin_ro` - read-only access to the API (fetching devices, groups, packages)
- `rdfm_admin_rw` - complete administrative access to the API with modification rights

Refer to the [RDFM Server API Reference chapter](api.rst) for a breakdown of the scopes required for accessing each API method.

### API authentication using Keycloak

#### Running the services

An example `docker-compose` file that can be used to run the RDFM server using [Keycloak Identity and Access Management server](https://www.keycloak.org/) as an authorization server is provided below, and in the `server/deploy/docker-compose.keycloak.development.yml` file.

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
      - RDFM_DISABLE_ENCRYPTION=1
      - RDFM_LOCAL_PACKAGE_DIR=/packages/
      - RDFM_OAUTH_URL=http://keycloak:8080/realms/master/protocol/openid-connect/token/introspect
      - RDFM_OAUTH_CLIENT_ID=rdfm-server-introspection
      - RDFM_OAUTH_CLIENT_SEC=<REPLACE_WITH_RDFM_INTROSPECTION_SECRET>
    networks:
      - rdfm
    ports:
      - "5000:5000"
    volumes:
      - db:/database/
      - pkgs:/packages/

  keycloak:
    image: quay.io/keycloak/keycloak:22.0.1
    restart: unless-stopped
    environment:
      - KEYCLOAK_ADMIN=admin
      - KEYCLOAK_ADMIN_PASSWORD=admin
    networks:
      - rdfm
    ports:
      - "8080:8080"
    command:
      - start-dev
    volumes:
      - keycloak:/opt/keycloak/data/

volumes:
  db:
  pkgs:
  keycloak:

networks:
  rdfm:
```

Before running the above services, you must first build the RDFM server container by running the following from the RDFM repository root folder:

```
docker build -f server/deploy/Dockerfile -t antmicro/rdfm-server:latest .
```

You can then run the services by running:

```
docker-compose -f server/deploy/docker-compose.keycloak.development.yml up
```

#### Keycloak configuration

Further configuration on the Keycloak server is required before any requests are successfully authenticated.
First, navigate to the Keycloak Administration Console found at `http://localhost:8080/` and login with the initial credentials provided in Keycloak's configuration above (by default: `admin`/`admin`).

Next, go to **Clients** and press **Create client**.
This client is required for the RDFM server to perform token validation.
The following settings must be set when configuring the client:
- **Client ID** - must match `RDFM_OAUTH_CLIENT_ID` provided in the RDFM server configuration, can be anything (for example: `rdfm-server-introspection`)
- **Client Authentication** - set to `On`
- **Authentication flow** - select only `Service accounts roles`

After saving the client, go to the `Credentials` tab found under the client details.
Make sure the authenticator used is `Client Id and Secret`, and copy the `Client secret`.
This secret must be configured in the RDFM server under the `RDFM_OAUTH_CLIENT_SEC` environment variable.

:::{note}
After changing the `docker-compose` variables, remember to restart the services (by pressing `Ctrl+C` and re-running the `docker-compose up` command).
:::

Additionally, you must create proper client scopes to define which users have access to the read-only and read-write parts of the RDFM API.
To do this, navigate to the `Client scopes` tab and select `Create client scope`.
Create two separate scopes with the following names; the rest of the settings can be left as default (if required, you may also add a description to the scope):
- `rdfm_admin_ro`
- `rdfm_admin_rw`

After restarting the services, the RDFM server will now validate requests against the Keycloak server.

#### Adding an API user

First, navigate to the Keycloak Administration Console found at `http://localhost:8080/` and login with the initial credentials provided in Keycloak's configuration above (by default: `admin`/`admin`).

Next, go to **Clients** and press **Create client**.
This client will represent a user of the RDFM API.
The following settings must be set when configuring the client:
- **Client Authentication** - set to `On`
- **Authentication flow** - select only `Service accounts roles`

After saving the client, go to the `Credentials` tab found under the client details.
Make sure the authenticator used is `Client Id and Secret`, and copy the `Client secret`.

Finally, assign the required scope to the client: under the `Client scopes` tab, click `Add client scope` and select one of the two RDFM scopes: read-only `rdfm_admin_ro` or read-write `rdfm_admin_rw`.

:::{note}
The newly-created client will now have access to the RDFM API.
To configure `rdfm-mgmt` to use this client, follow the [Configuration section](rdfm_manager.md#configuration) of the RDFM manager manual.
:::

## Configuring HTTPS

For simple deployments, the server can expose an HTTPS API directly without requiring an additional reverse proxy.
Configuration of the server's HTTPS can be done using the following environment variables:

- `RDFM_SERVER_CERT` - path to the server's signed certificate
- `RDFM_SERVER_KEY` - path to the server's private key

Both of these files must be accessible within the server Docker container.

### HTTPS demo deployment

:::{warning}
This demo deployment explicitly disables API authentication, and is only meant to be used as a reference on how to configure your particular deployment.
:::

An example HTTPS deployment can be found in the `server/deploy/docker-compose.https.development.yml` file.
Before running it, you must execute the `tests/certgen.sh` in the `server/deploy/` directory:

```bash
cd server/deploy/
../tests/certgen.sh
```

This script generates a root CA and an associated signed certificate to be used for running the server.
The following files are generated:

- `certs/CA.{crt,key}` - CA certificate/private key that is used as the root of trust
- `certs/SERVER.{crt,key}` - signed certificate/private key used by the server

To run the deployment, you must first build the RDFM server container by running the following from the RDFM repository root folder:

```bash
docker build -f server/deploy/Dockerfile -t antmicro/rdfm-server:latest .
```

You can then start the deployment by running:
```bash
docker-compose -f server/deploy/docker-compose.https.development.yml up
```

To verify the connection to the server, you must provide the CA certificate.
For example, when using `curl` to access API methods:

```bash
curl --cacert server/deploy/certs/CA.crt https://127.0.0.1:5000/api/v1/devices
```

When using `rdfm-mgmt`:

```bash
rdfm-mgmt --url https://127.0.0.1:5000/     \
          --cert server/deploy/certs/CA.crt \
          --no-api-auth                     \
          devices list
```

