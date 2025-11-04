### Test environment setup

The pytest tests for `rdfm-jwt-auth` and `rdfm-plotter` assume the presence of:

* Kcat
* Apptainer
* a Poetry virtual environment with `rdfm-plotter` dependencies installed
* a singularity image of Kafka with `rdfm-jwt-auth` callback and the custom `server.properties` passed

```
./tests/
├── conftest.py
├── test_kafka.sif
├── test-plotter.py
└── test-rdfm-jwt-auth.py
```

To find out how everything is built and ran, look at the [CI steps](../../.ci.yml) that are available at the root of the source tree.
The jobs of note are:

* `.install-poetry-and-apptainer`
* `build-rdfm-jwt-auth`
* `test-rdfm-plotter`
