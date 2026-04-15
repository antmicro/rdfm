### Setup

Install the required dependencies:

```sh
poetry install
```

And run with:

```
poetry run python src/rdfm_plotter/
```

Or install with:

```sh
pipx install .
```

And run with:

```sh
rdfm-plotter
```

### Examples

Ask for help:

```sh
rdfm-plotter --help
```

#### Print mode

Start printing the currently received records until interrupted:

```sh
rdfm-plotter --print --device 02:42:ac:17:00:03 --key CPU
```

Print records from the last hour:

```sh
rdfm-plotter --print --offset-hours 1 --device 02:42:ac:17:00:03 --key CPU
```

It will continue printing new records until interrupted. Example output of the above command:

```
| KEY: b'CPU' | TOPIC: 02-42-ac-17-00-03 | PARTITION: 0 | TIMESTAMP TYPE: LogAppendTime | TIMESTAMP: 1775643636020 | OFFSET: 1661
| device_time(millis):   1775643636017
| entry:                 {"sysstat":{"hosts":[{"nodename":"cb7375df33ee","sysname":"Linux","release":"6.1.0-43-amd64","machine":"x86_64","number-of-cpus":16,"date":"04/08/26","statistics":[{"timestamp":"10:20:36","cpu-load":[{"cpu":"all","usr":0.56,"nice":0,"sys":0.12,"iowait":0,"irq":0,"soft":0,"steal":0,"guest":0,"gnice":0,"idle":99.31}]}]}]}}
```

It's possible to apply a capture group to the `entry` field during printing:

```sh
# Extract the string from the "machine" key
rdfm-plotter --print --offset-hours 1 \
    --device 02:42:ac:17:00:03 --key CPU \
    --pattern '"machine":"([a-zA-z0-9]+)"'
#                         ^
#                         |
#                       This is a capture group, it captures what's inside the parentheses.
```

Example output of the above command:

```
| KEY: b'CPU' | TOPIC: 02-42-ac-17-00-03 | PARTITION: 0 | TIMESTAMP TYPE: LogAppendTime | TIMESTAMP: 1775643726015 | OFFSET: 1724
| device_time(millis):   1775643726011
| entry:                 {"sysstat":{"hosts":[{"nodename":"cb7375df33ee","sysname":"Linux","release":"6.1.0-43-amd64","machine":"x86_64","number-of-cpus":16,"date":"04/08/26","statistics":[{"timestamp":"10:22:06","cpu-load":[{"cpu":"all","usr":1.63,"nice":0,"sys":0.25,"iowait":0,"irq":0,"soft":0,"steal":0,"guest":0,"gnice":0,"idle":98.11}]}]}]}}
| extracted value:       x86_64
```

If a regular expression has more than a single capture group, it's possible to set which one should be extracted with the `--group` argument.

#### Plot mode

Inside plot mode, making use of regex capture groups is required. By default, what's captured is cast to a `float` for plotting purposes. That behavior can be overriden with an `--int` argument.

Example:

Plot CPU `usr` metric from records received the past hour:

```sh
rdfm-plotter --plot --offset-hours 1 --pattern '"usr":([0-9]+\.[0-9]+)' \
    --key CPU --device 02:42:ac:17:00:03
```

You can plot any number from `entry` provided you can write a regular expression capturing it.
