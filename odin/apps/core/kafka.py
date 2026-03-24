from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from kafka.structs import TopicPartition

from django.conf import settings


logger = logging.getLogger(__name__)


class PartitionKey(Enum):
    SENSORS = "sensors"
    RELAYS = "relays"


class MessageType(Enum):
    RELAY_STATE_UPDATE = "RELAY_STATE_UPDATE"
    SENSOR_DATA_UPDATE = "SENSOR_DATA_UPDATE"


class KafkaService:
    _producer: KafkaProducer | None = None
    _consumer: KafkaConsumer | None = None

    @classmethod
    def get_producer(cls) -> KafkaProducer:
        if cls._producer is None:
            cls._producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
            )
        return cls._producer

    @classmethod
    def get_consumer(cls) -> KafkaConsumer:
        if cls._consumer is None:
            cls._consumer = KafkaConsumer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
        return cls._consumer

    @classmethod
    def send_message(cls, topic: str, message: dict[str, Any], key: str | None = None) -> bool:
        try:
            producer = cls.get_producer()
            future = producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Message sent to topic {record_metadata.topic} "
                f"partition {record_metadata.partition} offset {record_metadata.offset}"
            )
            return True

        except KafkaError as e:
            logger.error(f"Kafka error: {e}")

        return False

    @classmethod
    def send_relay_update(cls, relay_id: str, target_state: str) -> None:
        message = {"relay_id": relay_id, "target_state": target_state}
        cls.send_message(settings.KAFKA_CORUSCANT_TOPIC, message=message, key=PartitionKey.RELAYS.value)

    @classmethod
    def get_relay_state_from_kafka(cls, relay_id: str, max_messages: int = 10) -> str | None:
        consumer = cls.get_consumer()
        try:
            partitions = consumer.partitions_for_topic(settings.KAFKA_ODIN_TOPIC)
            if not partitions:
                return None

            topic_partitions = [TopicPartition(settings.KAFKA_ODIN_TOPIC, p) for p in partitions]
            consumer.assign(topic_partitions)

            end_offsets = consumer.end_offsets(topic_partitions)
            for tp in topic_partitions:
                end_offset = end_offsets[tp]
                consumer.seek(tp, max(0, end_offset - 1))

            for _ in range(max_messages):
                records = consumer.poll(timeout_ms=1000)
                for _tp, messages in records.items():
                    for message in reversed(messages):
                        data = message.value.get("data", {})
                        if (
                            data.get("type") == MessageType.RELAY_STATE_UPDATE.value
                            and data.get("relay_id") == relay_id
                        ):
                            return data.get("state")

            return None

        except KafkaError as e:
            logger.error(f"Failed to get relay state from Kafka for relay {relay_id}: {e}")
            raise

        finally:
            consumer.close()
