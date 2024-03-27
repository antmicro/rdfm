# RDFM Management Server

## Introduction

The RDFM Management Server is a core part of the RDFM ecosystem. The server manages incoming device connections and grants authorization only to those which are allowed to check-in with the server.
It also handles package upload and management, deploy group management and other crucial functionality required for robust and secure device Over-The-Air (OTA) updates along with allowing remote system management without exposing devices to the outside world.

## REST API

The server exposes a management and device API that is used by management software and end devices. A comprehensive list of all API endpoints is available in the [RDFM Server API Reference chapter](api.rst).

## Setting up a Dockerized development environment

The preferred method for running the RDFM server is by using a Docker container.
To set up a local development environment, first clone the RDFM repository:

```bash
git clone https://github.com/antmicro/rdfm.git
cd rdfm/
```

A `Dockerfile` is provided in the `server/deploy/` directory that builds a container suitable for running the server.
Currently, it is required to build the container image manually.
To do this, run the following from the **cloned RDFM repository root** folder:

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
      - RDFM_WSGI_SERVER=werkzeug
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

## Configuration via environment variables

Configuration of the RDFM server can be changed by using the following environment variables:

- `RDFM_JWT_SECRET` - secret key used by the server when issuing JWT tokens, this value must be kept secret and not easily guessable (for example, a random hexadecimal string).
- `RDFM_DB_CONNSTRING` - database connection string, for examples please refer to: [SQLAlchemy - Backend-specific URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls). Currently, only the SQLite and PostgreSQL engines were verified to work with RDFM (however: the PostgreSQL engine requires adding additional dependencies which are currently not part of the default server image, this may change in the future).

Development configuration:

- `RDFM_DISABLE_ENCRYPTION` - if set, disables the use of HTTPS, falling back to exposing the API over HTTP. This can only be used in production if an additional HTTPS reverse proxy is used in front of the RDFM server.
- `RDFM_DISABLE_API_AUTH` - if set, disables request authentication on the exposed API routes. **WARNING: This is a development flag only! Do not use in production!** This causes all API methods to be freely accessible, without any access control in place!

HTTP/WSGI configuration:

- `RDFM_HOSTNAME` - hostname/IP address to listen on. This is additionally used for constructing package URLs when storing packages in a local directory.
- `RDFM_API_PORT` - API port.
- `RDFM_SERVER_CERT` - required when HTTPS is enabled; path to the server's certificate. The certificate can be stored on a Docker volume mounted to the container. For reference on generating the certificate/key pairs, see the `server/tests/certgen.sh` script.
- `RDFM_SERVER_KEY` - required when HTTPS is enabled; path to the server's private key. Additionally, the above also applies here.
- `RDFM_WSGI_SERVER` - WSGI server to use, this value should be left default. Accepted values: `gunicorn` (**default**, production-ready), `werkzeug` (recommended for development).
- `RDFM_WSGI_MAX_CONNECTIONS` - (when using Gunicorn) maximum amount of connections available to the server worker. This value must be set to at minimum the amount of devices that are expected to be maintaining a persistent (via WebSocket) connection with the server. Default: `4000`.

API OAuth2 configuration (must be present when `RDFM_DISABLE_API_AUTH` is omitted):

- `RDFM_OAUTH_URL` - specifies the URL to an authorization server endpoint compatible with the RFC 7662 OAuth2 Token Introspection extension. This endpoint is used to authorize access to the RDFM server based on tokens provided in requests made by API users.
- `RDFM_OAUTH_CLIENT_ID` - if the authorization server endpoint provided in `RDFM_OAUTH_URL` requires the RDFM server to authenticate, this variable defines the OAuth2 `client_id` used for authentication.
- `RDFM_OAUTH_CLIENT_SEC` -  if the authorization server endpoint provided in `RDFM_OAUTH_URL` requires the RDFM server to authenticate, this variable defines the OAuth2 `client_secret` used for authentication.

Package storage configuration:

- `RDFM_STORAGE_DRIVER` - storage driver to use for storing artifacts. Accepted values: `local` (default), `s3`.
- `RDFM_LOCAL_PACKAGE_DIR` - specifies a path (local for the server) to a directory where the packages are stored.
- `RDFM_S3_BUCKET` - when using S3 storage, name of the bucket to upload the packages to.
- `RDFM_S3_ACCESS_KEY_ID` - when using S3 storage, Access Key ID to access the specified bucket.
- `RDFM_S3_ACCESS_SECRET_KEY` - when using S3 storage, Secret Access Key to access the specified bucket.

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
docker-compose -f server/deploy/docker-compose.minio.development.yml up
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


## Production deployments

### Production considerations

The following is a list of considerations when deploying the RDFM server:

1. HTTPS **must** be enabled; `RDFM_DISABLE_ENCRYPTION` **must not** be set (or the server is behind a dedicated reverse proxy that adds HTTPS on the edge).
2. API authentication **must** be enabled; `RDFM_DISABLE_API_AUTH` **must not** be set.
3. RDFM **must** use a production WSGI server; `RDFM_WSGI_SERVER` **must not** be set  to `werkzeug`.
   When not provided, the server defaults to using a production-ready WSGI server (`gunicorn`).
   The development server (`werkzeug`) does not provide sufficient performance to handle production workloads, and a high percentage of requests will be dropped under heavy load.
4. RDFM **must** use a dedicated (S3) package storage location; the local directory driver does not provide adequate performance when compared to dedicated object storage.

Refer to the above configuration chapters for how to configure each aspect of the RDFM server:

1. [Configuring HTTPS](#configuring-https)
2. [Configuring API authentication](#configuring-api-authentication)
3. [Configuring the WSGI server](#configuration-via-environment-variables)
4. [Configuring S3 package storage](#configuring-package-storage-location)

A practical example of a deployment that includes all the above considerations can be found below, in the [Production example deployment](#production-example-deployment) section.

### Production example deployment

:::{warning}
For simplicity, this example deployment has static credentials pre-configured pretty much everywhere, and as such should never be used directly as a production setup.
At least the following secrets are pre-configured and would require changes:
- S3 Access Key ID/Access Secret Key
- rdfm-server JWT secret
- Keycloak Administrator username/password
- Keycloak Client: rdfm-server introspection Client ID/Secret
- Keycloak Client: rdfm-mgmt admin user Client ID/Secret

Additionally, the Keycloak server requires further configuration for production deployments.
For more information, refer to the [Configuring Keycloak for production](https://www.keycloak.org/server/configuration-production) page in Keycloak documentation.
:::

A reference setup is provided in `server/deploy/docker-compose.production.yml` that can be used for customizing production server deployments.
Prior to starting the deployment, you must generate a signed server certificate that will be used for establishing the HTTPS connection to the server.
This can be done by either providing your own certificate, or by running the provided example certificate generation script:

```bash
cd server/deploy/
../tests/certgen.sh
```

When using the `certgen.sh` script, the CA certificate found at `server/deploy/certs/CA.crt` can be used for validating the connection made to the server.

Similarly to previous example deployments, it can be started by running the following command from the **RDFM monorepository root folder**:

```bash
docker-compose -f server/deploy/docker-compose.production.yml up
```

`rdfm-mgmt` configuration for this deployment can be found in `server/deploy/test-rdfm-mgmt-config.json`.
After copying the configuration to `$HOME/.config/rdfm-mgmt/config.json`, you can access the server by running:

```bash
rdfm-mgmt --url https://127.0.0.1:5000/ --cert server/deploy/CA.crt \
          devices list
```

