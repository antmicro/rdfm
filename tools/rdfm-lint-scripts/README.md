### Install

```sh
pipx install .
```

### Usage

Ask for help:

```sh
rdfm-lint-mypy --help
rdfm-lint-pycodestyle --help
```

Run Pycodestyle with a custom config on some directory:

```sh
rdfm-lint-pycodestyle --config-file ~/Documents/pycodestyle --directory some_project/
```

Run MyPy on the current directory with a custom config:

```sh
rdfm-lint-mypy --config-file ~/Documents/mypy.ini
```

Run Pycodestyle, but exclude any files that end in `_pb2.py` or start with `_`:

```sh
rdfm-lint-pycodestyle --exclude '*_pb2.py,_*.py'
```

Analogous example with MyPy, the difference is that it makes use of regular expressions:

```sh
rdfm-lint-mypy --exclude '/(.+_pb2\.py)|(_.+\.py)$'
```

Run MyPy with a manually set Python executable from a virtual environment:

```sh
# MyPy needs a Python executable associated with a virtual environment that has used packages installed. They're needed for proper type checking.
export PYTHON_EXEC=some_project/.venv/bin/python
rdfm-lint-mypy --directory some_project/
```

If not provided, the tool will try to find it by itself inside `--directory` with Poetry.
