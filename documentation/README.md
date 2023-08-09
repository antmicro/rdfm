# RDFM Documentation

This folder contains sources required for building the RDFM documentation pages.

## Requirements

- `Poetry` dependency manager
- `Python3`

## Building

### 1. Activate the correct venv

Run the following command to activate the server venv:
```bash
cd server/
poetry shell
```

**Important note**: This venv must be active during the following steps of the build.

### 2. Installing documentation requirements

Install the required Python packages:

```bash
cd documentation/
pip3 install -r requirements.txt
pip3 install sphinxcontrib-httpdomain
```

### 3. Building the server package

In order to build the documentation, the server package must be built first, as part of the docs are automatically generated directly from the API module.

```bash
cd server/
poetry build
poetry install
```

### 4. Building documentation

Run the following command to build the docs in HTML and PDF format:

```bash
cd documentation/
make html latexpdf
```

`texlive` is required in order to build the pages in PDF format.
