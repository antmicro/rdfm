# RDFM Frontend

## Introduction

Repository contains code for a frontend application that is able to render data from and communicate with `rdfm-server` through HTTP requests.

The application uses HTTP Polling to dynamically detect any changes in the data and update the UI accordingly, so multiple users can use the application simultaneously (as well as the `rdfm-mgmt` tool).


To use the frontend application, make sure that `rdfm-server` is up and running.
Details on how to run it can be found in [RDFM Management Server](./rdfm_mgmt_server.md).
To be able to send requests to `rdfm-server` its URL has to be defined in the `.env` file using `VITE_SERVER_URL` key.

```{warning}
Currently no authentication is implemented in the frontend application, so make sure that the `RDFM_DISABLE_ENCRYPTION` and `RDFM_DISABLE_API_AUTH` values are set to `1`.
```

Before running any of the commands, make sure that you have `npm` installed.

## Building the application

To install dependencies and build the application for production run the following commands in the root directory of the project:

```bash
npm install
npm run build
```

The built static files are located in the `dist` directory.
To include the frontend application and access it using `rdfm-server`, a `RDFM_INCLUDE_FRONTEND_ENDPOINT` docker-compose variable has to be set.
As a consequence, the frontend application will be served on `/api/static/frontend` endpoint, one the HTTP server is started.

## Running development server

To install dependencies and start the development server run the following commands in the root directory of the project:

```bash
npm install
npm run dev
```

To communicate with `rdfm-server` when using a separate development server, make sure to set `RDFM_DISABLE_CORS` variable in docker-compose configuration.

```{warning}
`RDFM_DISABLE_CORS` variable should not be set in production environment, as it allows for cross-origin requests.
```

## Formatting

To format the code using `prettier` run the following command:

```bash
npm install
npm run format
```
