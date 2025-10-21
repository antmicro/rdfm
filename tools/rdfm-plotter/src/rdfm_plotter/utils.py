import time
from kafka import KafkaConsumer, TopicPartition
from kafka.consumer.fetcher import ConsumerRecord
from typing import Optional
from rdfm_plotter.config import ClientConfiguration
from rdfm_plotter.log_pb2 import log as Log  # type: ignore[attr-defined]


def log_deserializer(record: bytes) -> Log:
    log = Log()
    log.ParseFromString(record)
    return log


def get_current_utc_millis_at_offset(hours: int) -> int:
    """
    Subtracts the hours*milliseconds_in_an_hour from the current unix millis.
    """
    return int(time.time() - hours*3600)*1000


def deserialize(r: ConsumerRecord) -> Log:
    """
    Deserializes consumer record value according to protobuf schema.
    """
    log = Log()
    log.ParseFromString(r.value)
    return log


def sort_by_device_timestamp(logs: list[Log]) -> None:
    """
    Sorts the provided list in place by unix millis inside device_time.
    """
    logs.sort(key=lambda x: x.device_time.ToMilliseconds())


def flatten(d: dict[TopicPartition, list[ConsumerRecord]]) -> list[ConsumerRecord]:
    """
    Flattens the return value of KafkaConsumer.poll() to disregard the topic partitions.
    Not optimal. Ideally, with the knowledge of the wanted key, consumer should just
    calculate the hash from that key and only consume from the single wanted partition.
    """
    flat = []
    for k in d.keys():
        flat += d[k]
    return flat


def filter_record(record: ConsumerRecord) -> Optional[Log]:
    """
    Decide whether a record should be plotted/displayed based on the values of args inside
    ClientConfiguration.
    """
    # If a key argument was provided, check against it first
    args = ClientConfiguration().args
    if args.key and record.key != args.key:
        return None

    log = deserialize(record)

    if log.device_mac == args.device:
        return log
    return None


def consumer_seek_hours_delta(consumer: KafkaConsumer):
    """
    For the given consumer, shift the offsets of all partitions to the specified offset in the past.
    """
    millis = get_current_utc_millis_at_offset(ClientConfiguration().args.offset_hours)
    # CHANGEME: In the future this will be device mac addr
    partitions: set[int] = consumer.partitions_for_topic(ClientConfiguration().args.topic)
    offsets: dict[TopicPartition, OffsetAndTimestamp] = (
            consumer.offsets_for_times(
                dict(
                    map(
                        lambda p: (TopicPartition(ClientConfiguration().args.topic, p),
                                   millis), [*partitions])
                    )
                )
            )
    for part in offsets.keys():
        if offsets[part] is None:
            continue  # No records to seek to
        consumer.seek(part, offsets[part].offset)


def pretty_print_record(log: Log, record: ConsumerRecord, extracted: Optional[str] = None) -> None:
    """
    Print information about a record in human readable format
    """
    timestamp_type = "NotAvailable"
    match record.timestamp_type:
        case 0:
            timestamp_type = "CreateTime"
        case 1:
            timestamp_type = "LogAppendTime"

    print("| KEY: {} | TOPIC: {} | PARTITION: {} | TIMESTAMP TYPE: {} | TIMESTAMP: {} | OFFSET: {}"
          .format(
              record.key,
              record.topic,
              record.partition,
              timestamp_type,
              record.timestamp,
              record.offset))
    print(f"| device_mac:\t\t {log.device_mac}")
    print(f"| device_time(millis):\t {log.device_time.ToMilliseconds()}")
    print(f"| entry:\t\t {log.entry}")
    if extracted:
        print(f"| extracted value:\t {extracted}")
    print()
