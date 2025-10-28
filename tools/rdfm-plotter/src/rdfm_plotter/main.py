from rdfm_plotter.rdfm_consumer import (
    RdfmConsumer,
    ClientConfiguration
)
from rdfm_plotter.utils import (
    filter_record,
    flatten,
    sort_by_device_timestamp,
    pretty_print_record
)
from servis import render_time_series_plot_with_histogram


def main() -> None:
    if ClientConfiguration().args.plain:
        consumer = RdfmConsumer.plain_create()
    else:
        consumer = RdfmConsumer.quick_create()
    if ClientConfiguration().args.print:
        print_records(consumer)
    elif ClientConfiguration().args.plot:
        plot_records(consumer)


def print_records(consumer: RdfmConsumer):
    exit_code = 0
    args = ClientConfiguration().args
    try:
        for record in consumer:
            log = filter_record(record)
            if not log:
                continue
            value = None
            if args.pattern is not None:
                result = args.pattern.search(log.entry)
                if not result:
                    # Pattern search didn't return aything, skip
                    continue
                value = result.group(args.group)
            pretty_print_record(log, record, value)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        exit_code = 1
        print(f"Encountered an exception: {e}")
    finally:
        consumer.close()
        exit(exit_code)


def plot_records(consumer: RdfmConsumer):
    logs = []
    args = ClientConfiguration().args
    while True:
        try:
            records = consumer.poll(timeout_ms=args.poll_timeout)
            if not records:
                break

            flat = flatten(records)

            for record in flat:
                log = filter_record(record)
                if log:
                    logs.append(log)

        except Exception as e:
            consumer.close()
            print(f"Encountered an exception: {e}")
            exit(1)

    sort_by_device_timestamp(logs)

    values = []
    timestamps = []

    for log in logs:
        result = args.pattern.search(log.entry)
        if not result:
            # Pattern search didn't return aything, skip
            continue
        value = result.group(args.group)
        if args.int:
            value = int(value)
        elif args.float:
            value = float(value)
        values.append(value)
        timestamps.append(log.device_time.ToSeconds())

    try:
        render_time_series_plot_with_histogram(values, timestamps, is_x_timestamp=True)
    except IndexError:
        print(("Encountered an IndexError exception, most likely nothing to plot."
               " Did you set the offset? (-o||--offset-hours)"))
    finally:
        consumer.close()
