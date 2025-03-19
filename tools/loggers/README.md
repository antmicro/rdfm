# RDFM default logging utility

For use by RDFM Linux clients to send usage statistics such as CPU, MEM, FS.

## Build

```bash
cd tools/loggers
make
```

## Run

```bash
$ ./loggers --help
Usage of ./loggers:
  -cpu
        report CPU usage
  -duration int
        time to gather data in seconds (default 5)
  -fs
        report filesystem usage
  -mem
        report memory usage
  -t    include time

$ ./loggers --cpu --duration=3
cpu:all,tags
0.31250000021827873,"{}"
0.12438118823408029,"{}"
```
