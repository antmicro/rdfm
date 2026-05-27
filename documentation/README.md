# RDFM Documentation

This folder contains sources required for building the RDFM documentation pages.

## Requirements

- Poetry dependency manager
- Python3
- GNU Make

## Building

### 1. Installing documentation requirements

Install the required Python packages:

```bash
cd documentation/
poetry install
```

### 2. Building documentation

Run the following command to build the docs in HTML and PDF format:

```bash
cd documentation/
poetry run make html latexpdf
```

`texlive` is also required in order to build the pages in PDF format.
