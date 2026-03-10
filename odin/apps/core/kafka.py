from __future__ import annotations

import json
import logging
from typing import Any

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from kafka.structs import TopicPartition

from django.conf import settings


logger = logging.getLogger(__name__)


class KafkaService:
    _producer: KafkaProducer | None = None

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
    def send_message(cls, topic: str, message: dict[str, Any]) -> None:
        try:
            producer = cls.get_producer()
            future = producer.send(topic, value=message)
            future.get(timeout=10)
            logger.info(f"Kafka message sent to topic '{topic}': {message}")
        except KafkaError as e:
            logger.error(f"Failed to send Kafka message to topic '{topic}': {e}")
            raise

    @classmethod
    def send_relay_update(cls, relay_id: str, target_state: str) -> None:
        message = {"relay_id": relay_id, "target_state": target_state}
        cls.send_message(settings.KAFKA_RELAY_TOPIC, message)

    @classmethod
    def get_relay_state_from_kafka(cls, relay_id: str) -> str | None:
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
            )
            consumer.subscribe(settings.KAFKA_ODIN_TOPIC)

            partitions = consumer.partitions_for_topic(settings.KAFKA_ODIN_TOPIC)
            if not partitions:
                consumer.close()
                return None

            topic_partitions = [TopicPartition(settings.KAFKA_ODIN_TOPIC, p) for p in partitions]
            consumer.assign(topic_partitions)
            consumer.seek_to_end(topic_partitions)

            for _ in range(100):
                records = consumer.poll(timeout_ms=1000)
                for _tp, messages in records.items():
                    for message in reversed(messages):
                        data = message.value
                        if data.get("relay_id") == relay_id:
                            state = data.get("state")
                            consumer.close()
                            return state

            consumer.close()
            return None
        except KafkaError as e:
            logger.error(f"Failed to get relay state from Kafka for relay {relay_id}: {e}")
            raise
