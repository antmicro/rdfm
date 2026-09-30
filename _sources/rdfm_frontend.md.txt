# RDFM Frontend

## Introduction

Repository contains code for a frontend application that is able to render data from and communicate with `rdfm-server` through HTTP requests.

The application uses HTTP Polling to dynamically detect any changes in the data and update the UI accordingly, so multiple users can use the application simultaneously (as well as the `rdfm-mgmt` tool).


To use the frontend application, make sure that `rdfm-server` is up and running.
Details on how to run it can be found in [RDFM Management Server](./rdfm_mgmt_server.md).
To be able to send requests to `rdfm-server` its URL has to be defined in the `.env` file using `VITE_SERVER_URL` key.

```{warning}
If no authentication is used in the frontend application make sure that the `RDFM_DISABLE_ENCRYPTION` and `RDFM_DISABLE_API_AUTH` values are set to `1`.
```

Before running any of the commands, make sure that you have `npm` installed.

## Building the application

To install dependencies and build the application for production run the following commands in the root directory of the project:

```bash
npm install
npm run build
```

The built static files are located in the `dist` directory.
The frontend can be started alongside the RDFM API in the same [Docker image](rdfm_mgmt_server.md#setting-up-a-dockerized-development-environment).
The following changes must be applied:

- `VITE_RDFM_BACKEND` in the `.env` file to `'true'`.
- `VITE_SERVER_URL` in the `.env` file to the URL of the backend server.
- `RDFM_INCLUDE_FRONTEND_ENDPOINT` in the docker-compose configuration. As a consequence, the frontend application will be served on `/api/static/frontend` endpoint once the HTTP server is started.

The frontend may also be deployed independently of the RDFM API.
The following configuration settings must then be set:

- `VITE_RDFM_BACKEND` in the `.env` file to `'false'`.
- `VITE_SERVER_URL` in the `.env` file to the URL of the backend server.
- `RDFM_ENABLE_CORS` in the docker-compose configuration to `1` to enable CORS requests.
- `RDFM_FRONTEND_APP_URL` in the docker-compose configuration to the URL of the frontend application server, as it is used for redirects.

```{warning}
`RDFM_ENABLE_CORS` variable should not be set in production environment, as it allows for cross-origin requests.
```

## Running development server

When developing the application it is recommended to use the `vite` development server, as features like Hot Module Replacement is enabled.
To install dependencies and start the development server run the following commands in the root directory of the project:

```bash
npm install
npm run dev
```

To communicate with `rdfm-server` when using the development server, make sure to set all variables as described in the [Building](#building-the-application) section in the same as it is done for a separate server deployment.


## Configuration

The frontend application can be configured using an `.env` file.
That file contains variables that can be set to change the behavior of the application.
Below there is a description of all available variables.

* `VITE_SERVER_URL` - RDFM server URL
* `VITE_RDFM_BACKEND` - Indicates if the backend hosts the frontend application
* `VITE_LOGIN_URL` - OIDC login URL
* `VITE_LOGOUT_URL` - OIDC logout URL
* `VITE_OAUTH2_CLIENT` - OAUTH2 Client ID
* `VITE_CUSTOM_FAVICON` - (Optional) An URL to an image. If supplied will override the default RDFM favicon
* `VITE_CUSTOM_STYLESHEET` - (Optional) An URL to a CSS stylesheet. If supplied will be appended to page's head tag
* `VITE_CUSTOM_LOGO` - (Optional) An URL to an image. If supplied will override the default RDFM logo

## Formatting

To format the code using `prettier` run the following command:

```bash
npm install
npm run format
```
