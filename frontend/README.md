# frontend

Repository contains code for a frontend application that is able to render data from and communicate with `rdfm-server` through HTTP requests.

The application uses HTTP Polling to dynamically detect any changes in the data and update the UI accordingly, so multiple users can use the application simultaneously (as well as the `rdfm-mgmt` tool).


To use the frontend application, make sure that `rdfm-server` is up and running.
Details on how to run it using docker-compose can be found in the `rdfm` README file.
To be able to send requests to `rdfm-server` its URL has to be defined in the `.env` file using `VITE_SERVER_URL` key.

```danger
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
To be able to run the application and communicate with `rdfm-server` the `dist/index.html` file has to be served using a web server.
For example using `http.server` package from python:

```bash
cd dist
python -m http.server 8080
```

Visiting the `http://localhost:8080` should display the application.

```danger
Make sure that `0.0.0.0` address is not used, as it is known to cause CORS issues.
```

## Running development server
To install dependencies and start the development server run the following commands in the root directory of the project:

```bash
npm install
npm run dev
```

## Formatting

To format the code using `prettier` run the following command:

```bash
npm install
npm run format
```
