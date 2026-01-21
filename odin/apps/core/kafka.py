from __future__ import annotations

import json
import logging
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError

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
