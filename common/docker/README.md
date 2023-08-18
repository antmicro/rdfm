# RDFM CI Docker image

This folder contains scripts and files required for running RDFM CI workflows.

## Building the Docker image

Run the following command to build the CI container image:

```bash
docker build --tag rdfm-ci-base:latest --file Dockerfile .
```

The image tag may need to be adjusted depending on the CI engine that the image will be deployed to.
