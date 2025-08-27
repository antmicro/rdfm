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
rdfm-plotter --print --topic RDFM --device 00:00:00:00:00:02 --key CPU
```

Print records from the last hour:

```sh
rdfm-plotter --print --topic RDFM --offset-hours 1 --device 00:00:00:00:00:02 --key CPU
```

It will continue printing new records until interrupted. Example output of the above command:

```
| KEY: b'CPU' | TOPIC: RDFM | PARTITION: 0 | TIMESTAMP TYPE: LogAppendTime | TIMESTAMP: 1757422138218 | OFFSET: 66837
| device_mac:            00:00:00:00:00:02
| device_time(millis):   1757429412544
| entry:                 {"sysstat":{"hosts":[{"nodename":"renodeunmatched","sysname":"Linux","release":"6.6.21-00001-g7b43b6e32bba","machine":"riscv64","number-of-cpus":4,"date":"09/09/25","statistics":[{"timestamp":"14:50:12","cpu-load":[{"cpu":"all","usr":99.02,"nice":0.00,"sys":0.98,"iowait":0.00,"irq":0.00,"soft":0.00,"steal":0.00,"guest":0.00,"gnice":0.00,"idle":0.00}]}]}]}}
```

It's possible to apply a capture group to the `entry` field during printing:

```sh
# Extract the string from the "machine" key
rdfm-plotter --print --topic RDFM --offset-hours 1 \
    --device 00:00:00:00:00:02 --key CPU \
    --pattern '"machine":"([a-zA-z0-9]+)"'
#                         ^
#                         |
#                       This is a capture group, it captures what's inside the parentheses.
```

Example output of the above command:

```
| KEY: b'CPU' | TOPIC: RDFM | PARTITION: 0 | TIMESTAMP TYPE: LogAppendTime | TIMESTAMP: 1757421941132 | OFFSET: 66691
| device_mac:            00:00:00:00:00:02
| device_time(millis):   1757429214445
| entry:                 {"sysstat":{"hosts":[{"nodename":"renodeunmatched","sysname":"Linux","release":"6.6.21-00001-g7b43b6e32bba","machine":"riscv64","number-of-cpus":4,"date":"09/09/25","statistics":[{"timestamp":"14:46:54","cpu-load":[{"cpu":"all","usr":8.00,"nice":0.00,"sys":1.00,"iowait":0.00,"irq":0.00,"soft":0.00,"steal":0.00,"guest":0.00,"gnice":0.00,"idle":91.00}]}]}]}}
| extracted value:       riscv64
```

If a regular expression has more than a single capture group, it's possible to set which one should be extracted with the `--group` argument.

#### Plot mode

Inside plot mode, making use of regex capture groups is required. By default, what's captured is cast to a `float` for plotting purposes. That behavior can be overriden with an `--int` argument.

Example:

Plot CPU `usr` metric from records received the past hour:

```sh
rdfm-plotter --plot --topic RDFM --offset-hours 1 \
    --pattern '"usr":([0-9]+\.[0-9]+)' --key CPU --device 00:00:00:00:00:02
```

You can plot any number from `entry` provided you can write a regular expression capturing it.
