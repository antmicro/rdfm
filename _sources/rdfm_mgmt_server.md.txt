# RDFM Management Server

## Introduction

The RDFM Management Server is a core part of the RDFM ecosystem.
The server manages incoming device connections and grants authorization only to those which are allowed to check in with the server.
It also handles package upload and management, deploy group management and other crucial functionality required for robust and secure device Over-The-Air (OTA) updates along with allowing remote system management without exposing devices to the outside world.

## REST API

The server exposes a management and device API used by management software and end devices.
A comprehensive list of all API endpoints is available in the [RDFM Server API Reference chapter](api.rst).

## Setting up a Dockerized development environment

The preferred method for running the RDFM server is by using a Docker container.
To set up a local development environment, first clone the RDFM repository:

```bash
git clone https://github.com/antmicro/rdfm.git
cd rdfm/
```

A `Dockerfile` is provided in the `server/deploy/` directory, that builds a container suitable for running the server.
Currently, it is required to build the container image manually.
To do this, run the following from the **cloned RDFM repository root** folder:

```bash
docker build -f server/deploy/Dockerfile -t antmicro/rdfm-server:latest .
```

A simple `docker-compose` file that can be used to run the server is provided below and in the `server/deploy/docker-compose.development.yml` file.

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

You can then start the server using the following command:

```bash
docker-compose -f server/deploy/docker-compose.development.yml up
```

## Configuration via environment variables

You can change the configuration of the RDFM server by using the following environment variables:

- `RDFM_JWT_SECRET` - secret key used by the server when issuing JWT tokens, this value must be kept secret and not easily guessable (for example, a random hexadecimal string).
- `RDFM_DB_CONNSTRING` - database connection string, for examples please refer to: [SQLAlchemy - Backend-specific URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls). Currently, only the SQLite and PostgreSQL engines were verified to work with RDFM (however, the PostgreSQL engine requires adding additional dependencies which are currently not part of the default server image - this may change in the future).

Development configuration:

- `RDFM_DISABLE_ENCRYPTION` - if set, disables the use of HTTPS, falling back to exposing the API over HTTP. This can only be used in production if an additional HTTPS reverse proxy is used in front of the RDFM server.
- `RDFM_DISABLE_API_AUTH` - if set, disables request authentication on the exposed API routes. **WARNING: This is a development flag only! Do not use in production!** This causes all API methods to be freely accessible, without any access control in place!
- `RDFM_ENABLE_CORS` - if set, disables CORS checks, which in consequence allows any origin to access the server. **WARNING: This is a development flag only! Do not use in production!**

HTTP/WSGI configuration:

- `RDFM_HOSTNAME` - hostname/IP address to listen on. This is additionally used for constructing package URLs when storing packages in a local directory.
- `RDFM_API_PORT` - API port.
- `RDFM_SERVER_CERT` - required when HTTPS is enabled; path to the server's certificate. The certificate can be stored on a Docker volume mounted to the container. For reference on generating the certificate/key pairs, see the `server/tests/certgen.sh` script.
- `RDFM_SERVER_KEY` - required when HTTPS is enabled; path to the server's private key. Additionally, the above also applies here.
- `RDFM_WSGI_SERVER` - WSGI server to use, this value should be left default. Accepted values: `gunicorn` (**default**, production-ready), `werkzeug` (recommended for development).
- `RDFM_WSGI_MAX_CONNECTIONS` - (when using Gunicorn) maximum amount of connections available to the server worker. This value must be set to at minimum the amount of devices that are expected to be maintaining a persistent (via WebSocket) connection with the server. Default: `4000`.
- `RDFM_GUNICORN_WORKER_TIMEOUT` - (when using Gunicorn) maximum allowed timeout of request handling on the server worker. Configuring this option may be necessary when uploading large packages.
- `RDFM_INCLUDE_FRONTEND_ENDPOINT` - specifies whether the RDFM server should serve the frontend application. If set, the server will serve the frontend application from endpoint `/api/static/frontend`. Before setting this variable, the frontend application must be built and placed in the `frontend/dist` directory.
- `RDFM_FRONTEND_APP_URL` - specifies URL to the frontend application. This variable is required when `RDFM_INCLUDE_FRONTEND_ENDPOINT` is not set, as backend HTTP server has to know where to redirect the **user**.

API OAuth2 configuration (must be present when `RDFM_DISABLE_API_AUTH` is omitted):

- `RDFM_OAUTH_URL` - specifies the URL to an authorization server endpoint compatible with the RFC 7662 OAuth2 Token Introspection extension. This endpoint is used to authorize access to the RDFM server based on tokens provided in requests made by API users.
- `RDFM_LOGIN_URL` - specifies the URL to a login page of the authorization server. It is used to authorize users and generate an access token and start a session.
- `RDFM_LOGOUT_URL` - specified the URL to a logout page of the authorization server. It is used to end the session and revoke the access token.
- `RDFM_OAUTH_CLIENT_ID` - if the authorization server endpoint provided in `RDFM_OAUTH_URL` requires the RDFM server to authenticate, this variable defines the OAuth2 `client_id` used for authentication.
- `RDFM_OAUTH_CLIENT_SEC` - if the authorization server endpoint provided in `RDFM_OAUTH_URL` requires the RDFM server to authenticate, this variable defines the OAuth2 `client_secret` used for authentication.

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
The following environment variables enable changing the configuration of the S3 integration:

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

### Users' and applications' permissions

The authorization server needs to implement certain applications' scopes and users' permissions for users and applications to access RDFM API.

#### Scopes

The following scopes are used for controlling access to different methods of the RDFM API:

- `rdfm_admin_ro` - read-only access to the API (fetching devices, groups, packages).
- `rdfm_admin_rw` - complete administrative access to the API with modification rights.

Additional rules are defined for package uploading route from [Packages API](api.rst#Packages_API):

- `rdfm_upload_single_file` - allows uploading an artifact of type `single-file`.
- `rdfm_upload_rootfs_image` - allows uploading artifacts `rootfs-image` and `delta-rootfs-image`.
Each package type requires its corresponding scope, or the complete admin access - `rdfm_admin_rw`.

Refer to the [RDFM Server API Reference chapter](api.rst) for a breakdown of the scopes required for accessing each API method.

#### Permissions

In addition to the above, you can assign specific permissions to users for specific resources (devices, groups, packages).
There are three types of permissions:

* **`read`** permission - Allows listing devices, groups, and packages, as well as downloading packages.
* **`update`** permission - Allows changing, adding, and updating groups and packages.
* **`delete`** permission - Allows deleting groups and packages.

These permissions are not mutually exclusive and have no hierarchy (none of the above permissions imply or contain the other).

Permissions to a group also apply to the devices and packages within that group.
For example, if you assign a user an `update` permission to a group, they will also be able to update any resources within that group.
These propagated permissions are implicit and are not stored in the RDFM Management Server.

You can inspect the current permissions for each user using the [Permissions API](api.rst#Permissions_API).

##### Assigning a Permission

To assign a permission to a user, you must have the `rdfm_admin_rw` scope. Then, you will need the following information:

* The **ID of the user** you want to assign the permission to, which you can obtain from your OAuth2 provider's administration panel.
* The **ID of the resource**, which can be retrieved via:
  * The [RDFM Manager](rdfm_manager.md) - Use the `rdfm-mgmt {devices,packages,groups} list` command to get a list of resources and their IDs.
  * The [RDFM Server API](api.rst) - The `/api/{v2,v1}/{devices,packages,groups}` endpoints will return a list of resources and their IDs.

Permissions can be assigned via a POST request to `/api/v1/permissions`.
For an example of such request, see [this endpoint's documentation](api.rst#post--api-v1-permissions).

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
      - ../keycloak-themes:/opt/keycloak/themes

volumes:
  db:
  pkgs:
  keycloak:

networks:
  rdfm:
```

Before running the services above, you must first build the RDFM server container by running the following from the RDFM repository root folder:

```
docker build -f server/deploy/Dockerfile -t antmicro/rdfm-server:latest .
```

You can then run the services by executing:

```
docker-compose -f server/deploy/docker-compose.keycloak.development.yml up
```

#### Keycloak configuration

Before any requests are successfully authenticated, you need to configure the Keycloak server further.
First, navigate to the Keycloak Administration Console found at `http://localhost:8080/` and log in with the initial credentials provided in Keycloak's configuration above (by default: `admin`/`admin`).

Next, go to **Clients** and press **Create client**.
This client is required for the RDFM server to perform token validation.
The following settings must be set when configuring the client:

- **Client ID** - must match `RDFM_OAUTH_CLIENT_ID` provided in the RDFM server configuration, can be anything (for example: `rdfm-server-introspection`)
- **Client Authentication** - set to `On`
- **Authentication flow** - select only `Service accounts roles`

After saving the client, go to the `Credentials` tab found in the client details.
Make sure the authenticator used is `Client Id and Secret` and copy the `Client secret`.
This secret must be configured in the RDFM server in the `RDFM_OAUTH_CLIENT_SEC` environment variable.

:::{note}
After changing the `docker-compose` variables, remember to restart the services (by pressing `Ctrl+C` and re-running the `docker-compose up` command).
:::

Additionally, you must create proper client scopes and user roles to define which users have access to the read-only and read-write parts of the RDFM API.
To create new scopes, navigate to the `Client scopes` tab and select `Create client scope`.
Create four separate scopes with the names listed below.
The rest of the settings can be left as default (if required, you may also add a description to the scope):

- `rdfm_admin_ro`
- `rdfm_admin_rw`
- `rdfm_upload_single_file`
- `rdfm_upload_rootfs_image`

To create new roles, navigate to the `Realm roles` tab and select `Create role`.
Create separate roles with the same names.
The rest of the settings can remain default (if required, you may also add a description to the role).

After restarting the services, the RDFM server will now validate requests against the Keycloak server.
To further set up the `rdfm-mgmt` manager to use the Keycloak server, refer to the [RDFM manager manual](rdfm_manager.md).
To add users with roles to the Keycloak server, which can then be used to access the RDFM API using the frontend application, refer to the [Adding a User](#adding-a-user) section below.

#### Adding an API client

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

#### Adding a User

First, navigate to the Keycloak Administration Console found at `http://localhost:8080/` and login with the initial credentials provided in Keycloak's configuration above (by default: `admin`/`admin`).

Next, go to the `Users` tab and press **Add user**.
This will open up a form to create a new user.
Fill in the **Username** field and press **Create**.

Next, go to the `Credentials` tab found under the user details and press **Set password**.
This form allows you to set a password for the user and determine whether creating a new one is required on the next login.

After configuring the user, go to the `Role mapping` tab under the user details.
There, appropriate roles can be assigned to the user using the **Assign role** button.

:::{note}
The newly created users can now log in using the RDFM frontend application.
To configure and run the frontend application, refer to the [RDFM Frontend chapter](rdfm_frontend.md).
:::

##### Configuring frontend application

When using the frontend application, logging in functionality is provided by the Keycloak server.
To integrate the Keycloak server with the frontend application first go to the client details created in the [Keycloak configuration](#keycloak-configuration) section.

Go to `Capability config` and make sure that **Implicit flow** and **Standard flow** are enabled.

Open the `Settings` panel and set **Valid redirect URIs** and **Valid post logout redirect URIs** values to the URL of the frontend application.
The value depends on the deployment method, if the `rdfm-server` is used to host the frontend application the value can be inferred from the `RDFM_HOSTNAME` and `RDFM_API_PORT` environment variables and will most likely be `http[s]://{RDFM_HOSTNAME}:{RDFM_API_PORT}`.
Otherwise, the value should be equal to `RDFM_FRONTEND_APP_URL` variable.

Additionally, you can change the theme of the login page to match the frontend application.
To do this, go to `Login settings` section and `rdfm` in the **Login theme** dropdown.

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
3. RDFM **must** use a production WSGI server; `RDFM_WSGI_SERVER` **must not** be set to `werkzeug`.
   When not provided, the server defaults to using a production-ready WSGI server (`gunicorn`).
   The development server (`werkzeug`) does not provide sufficient performance to handle production workloads, and a high percentage of requests will be dropped under heavy load.
4. RDFM **must** use a dedicated (S3) package storage location; the local directory driver does not provide adequate performance when compared to dedicated object storage.

Refer to the configuration chapters above for guidance on configuring each aspect of the RDFM server:

1. [HTTPS](#configuring-https)
2. [API authentication](#configuring-api-authentication)
3. [WSGI server](#configuration-via-environment-variables)
4. [S3 package storage](#configuring-package-storage-location)

You can find a practical example of a deployment that includes all the above considerations below.

### Production example deployment

:::{warning}
For simplicity, nearly all credentials for this example deployment are static and pre-configured, and as such should never be used directly in a production setup.
In such a scenario, at least the following pre-configured secrets need to be changed:

- S3 Access Key ID/Access Secret Key
- rdfm-server JWT secret
- Keycloak Administrator username/password
- Keycloak Client: rdfm-server introspection Client ID/Secret
- Keycloak Client: rdfm-mgmt admin user Client ID/Secret

Additionally, the Keycloak server requires further configuration for production deployments.
For more information, refer to the [Configuring Keycloak for production](https://www.keycloak.org/server/configuration-production) page in the Keycloak documentation.
:::

A reference setup that can be used for customizing production server deployments is provided in `server/deploy/docker-compose.production.yml`.
Prior to starting the deployment, you need to generate a signed server certificate that will be used for establishing the HTTPS connection to the server.
You can do it by either providing your own certificate, or by running the provided example certificate generation script:

```bash
cd server/deploy/
../tests/certgen.sh
../tests/certgen.sh certs IP.1:127.0.0.1 DEVICE no
```

When using the `certgen.sh` script, the CA certificate found at `server/deploy/certs/CA.crt` can be used for validating the connection made to the server.
The `server/deploy/certs/SERVER.crt` will be used as a certificate of the Management Server.

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

### A more advanced example of production deployment

In the `server/deploy/docker-compose.full.yml` file, you can find a more advanced example of the RDFM Management Server setup that includes the following:

* RDFM Management Server (`rdfm-server` service), using the `server/deploy/Dockerfile` to build the image
* Keycloak identity and access management server (`keycloak` service)
* PostgreSQL (`postgres` service) for the RDFM Management Server and Keycloak databases
* MinIO (`minio` service) object storage compatible with S3, along with a one-time service (`minio-bucket-creator`) that creates a bucket for RDFM updates
* nginx-based server for RDFM and Keycloak frontends (`frontend` service)

The `server/deploy/docker-compose.full.yml` file is accompanied by the `server/deploy/docker-compose.full.env` environment file, used to configure both the Docker Compose recipe and Docker containers running in the services.
Some variables provided in this `server/deploy/docker-compose.full.env` file require modifications to create a safe deployment environment.

:::{warning}
Similarly to the [Production example deployment](#production-example-deployment), for a safe environment you need to configure at least:

* `KEYCLOAK_ADMIN` - admin name in Keycloak
* `KEYCLOAK_ADMIN_PASSWORD` - password for admin in Keycloak
* `DB_USER` - username in the PostgreSQL database
* `DB_PASSWORD` - user password in the PostgreSQL database
* `RDFM_OAUTH_CLIENT_SEC` - secret key for the RDFM Management Server introspection client with name specified in `RDFM_OAUTH_CLIENT_ID`
* `RDFM_JWT_SECRET` - JWT secret for RDFM Management Server
* `RDFM_S3_ACCESS_KEY_ID` - access key for S3 bucket
* `RDFM_S3_ACCESS_SECRET_KEY` - secret key for S3 bucket

You also need to remove the `test-user-ro` and `test-user-rw` example users added in Keycloak's RDFM realm.

It is also recommended to change:

* `DB_NAME` - name of the RDFM Management Server database
* `RDFM_OAUTH_CLIENT_ID` - name of the introspection client in Keycloak for RDFM Management Server
* `KC_HTTP_RELATIVE_PATH` - relative path to the Keycloak Administration Console
:::

To set up and run this Docker Compose recipe:

* Adjust variables in `server/deploy/docker-compose.full.env`.
  :::{note}
  For development purposes, changing only `PUBLIC_ADDRESS` to hostname of the given device should suffice.
  :::
* Provide certificates for services in `./server/deploy/certs` directory:
  * The pairs of `crt` and `key` files are required for the services:
    * `SERVER` - for RDFM Management Server
    * `MINIO` - for MinIO service
    * `KEYCLOAK` - for Keycloak service
    * `FRONTEND` - for nginx service
  * If custom Certificate Authority was used to generate certificates, the `CA.crt` file(s) needs to be provided
  * The following certificates can be obtained from official Certificate Authority (such as Let's Encrypt)
  * They can also be generated locally using `./server/tests/certgen.sh` script:
    * Create certificates for all services (`$HOST` is used here for demo purposes, since some of the services require DNS name instead of localhost or loopback addresses to run in production mode):
      ```bash
      ./server/tests/certgen.sh ./server/deploy/certs/ DNS.1:$HOST DEVICE no MINIO DNS.1:minio KEYCLOAK DNS.1:keycloak FRONTEND DNS.1:$HOST
      ```
    * Adjust certificate for `minio` service (direct output from `../tests/certgen.sh` is not loadable by Minio service):
      ```bash
      openssl ec -in ./server/deploy/certs/MINIO.key -out ./server/deploy/certs/MINIO.key
      ```
    :::{warning}
    `CA.key` file generated by the script is confidential and cannot be shared in production use cases.
    :::
* Build Docker images for all services:
  ```bash
  docker-compose --env-file ./server/deploy/docker-compose.full.env -f ./server/deploy/docker-compose.full.yml build
  ```
* Start Docker Compose services:
  ```bash
  docker-compose --env-file server/deploy/docker-compose.full.env -f server/deploy/docker-compose.full.yml up
  ```
  Optionally, to run services in the background, use the `-d` flag:
  ```bash
  docker-compose --env-file server/deploy/docker-compose.full.env -f server/deploy/docker-compose.full.yml up -d
  ```

Once all services have started, the following addresses should become available:

* `https://${PUBLIC_ADDRESS}` - main page for the RDFM Management Server (`https://rdfm.com` with default values)
* `https://${PUBLIC_ADDRESS}${KC_RELATIVE_PATH}` - address to Keycloak's Administration Console, `https://rdfm.com/kc` with default values

To log into the RDFM Management Server, use one of the following test users (password is same as the username):

* `test-user-rw` - a test user with `rdfm_admin_rw` permissions
* `test-user-ro` - a test user with `rdfm_admin_ro` permissions

To stop services, either stop the `docker-compose` application or run:

```bash
docker-compose --env-file server/deploy/docker-compose.full.env -f server/deploy/docker-compose.full.yml down
```

To remove volumes associated with containers, add the `-v` flag:

```bash
docker-compose --env-file server/deploy/docker-compose.full.env -f server/deploy/docker-compose.full.yml down -v
```

Notes regarding this Docker Compose recipe:

* In this setup, all services run using the HTTPS protocol.
  Depending on which services will be exposed externally, this can be changed.
* By default, exposing just the port associated with the `frontend` service should suffice - it provides access to the RDFM Management Server, RDFM Management Server API, as well as Keycloak's Administration Console.
* Any of the services presented above can be replaced with compatible alternatives, i.e. `minio` can be replaced with Amazon S3, or `postgres` can be replaced with Amazon Aurora.
