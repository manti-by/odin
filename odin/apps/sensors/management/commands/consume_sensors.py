from __future__ import annotations

import json
import logging
import signal
import sys
from datetime import datetime
from typing import Any

from redis.exceptions import RedisError, ResponseError

from command_log.management.commands import LoggedCommand
from django.conf import settings
from django.db.utils import DatabaseError
from django.utils import timezone

from odin.apps.core.redis_bus import MessageType, RedisBus
from odin.apps.sensors.models import SensorLog


logger = logging.getLogger(__name__)

CONSUMER_GROUP = "sensor-consumers"
CONSUMER_NAME = "consume-sensors"
PENDING_RECLAIM_IDLE_MS = 5000
MAX_PROCESS_ATTEMPTS = 3
DEAD_LETTER_SUFFIX = ":dead"


class Command(LoggedCommand):
    help = "Runs a Redis stream consumer to listen for sensor data updates."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.running: bool = True
        self.client: Any | None = None

    def handle(self, *args: Any, **options: Any) -> None:
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("Starting Redis sensor consumer...")
        self.client = RedisBus.get_redis()
        stream = settings.REDIS_SENSORS_CHANNEL
        try:
            self.client.xgroup_create(stream, CONSUMER_GROUP, id="0", mkstream=True)
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            logger.info(f"Consumer group {CONSUMER_GROUP} already exists for stream {stream}")
        logger.info(f"Consuming stream: {stream}")

        try:
            self.drain_pending(stream)
            while self.running:
                if self.client is None:
                    raise RuntimeError("Redis client not initialized")
                self.reclaim_pending(stream)
                entries = self.client.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    streams={stream: ">"},
                    count=10,
                    block=1000,
                )
                if not entries:
                    continue
                self.process_entries(stream, entries)

        except (RedisError, OSError) as e:
            self.stderr.write(f"Redis error: {e}")
            sys.exit(1)
        finally:
            self.cleanup()

    def drain_pending(self, stream: str) -> None:
        """Process messages left unacked in the group before reading new ones."""
        if self.client is None:
            raise RuntimeError("Redis client not initialized")
        while self.running:
            entries = self.client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={stream: "0"},
                count=10,
            )
            if not entries:
                return
            if all(len(messages) == 0 for _, messages in entries):
                return
            if not self.process_entries(stream, entries):
                return

    def reclaim_pending(self, stream: str) -> None:
        """Retry messages that failed processing and are idle in the PEL."""
        if self.client is None:
            raise RuntimeError("Redis client not initialized")
        _next_id, messages, _deleted = self.client.xautoclaim(
            stream,
            CONSUMER_GROUP,
            CONSUMER_NAME,
            min_idle_time=PENDING_RECLAIM_IDLE_MS,
            start_id="0-0",
            count=10,
        )
        if messages:
            self.process_entries(stream, [[stream, messages]])

    def process_entries(self, stream: str, entries: Any) -> bool:
        """Process a batch of messages. Returns False if any entry was left pending."""
        if self.client is None:
            raise RuntimeError("Redis client not initialized")
        all_acked = True
        for _stream, messages in entries:
            for message_id, fields in messages:
                try:
                    payload = json.loads(fields[b"data"])
                except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Skipping malformed sensor message {message_id}: {e}")
                    self.client.xack(stream, CONSUMER_GROUP, message_id)
                    continue
                if not isinstance(payload, dict):
                    logger.warning(f"Skipping sensor message {message_id} with non-dict payload")
                    self.client.xack(stream, CONSUMER_GROUP, message_id)
                    continue
                if payload.get("type") != MessageType.SENSOR_DATA_UPDATE.value:
                    logger.warning(f"Skipping sensor message {message_id} with unexpected type {payload.get('type')!r}")
                    self.client.xack(stream, CONSUMER_GROUP, message_id)
                    continue
                try:
                    self.process_message(message=payload)
                except (ValueError, TypeError, AttributeError, DatabaseError) as e:
                    self.dead_letter_or_retry(stream, message_id, fields, e)
                    all_acked = False
                    continue
                self.clear_attempts(stream, message_id)
                self.client.xack(stream, CONSUMER_GROUP, message_id)
        return all_acked

    def dead_letter_or_retry(
        self, stream: str, message_id: bytes, fields: dict[bytes, bytes], error: Exception
    ) -> None:
        """Ack a permanently failing message to the dead-letter stream, else leave it pending."""
        if self.client is None:
            raise RuntimeError("Redis client not initialized")
        attempts = self.increment_attempts(stream, message_id)
        if attempts < MAX_PROCESS_ATTEMPTS:
            logger.error(
                f"Failed to process sensor message {message_id} (attempt {attempts}/{MAX_PROCESS_ATTEMPTS}): {error}"
            )
            return

        logger.error(
            f"Moving sensor message {message_id} to dead-letter stream after {attempts} failed attempts: {error}"
        )
        self.client.xack(stream, CONSUMER_GROUP, message_id)
        self.client.xadd(
            f"{stream}{DEAD_LETTER_SUFFIX}",
            {"message_id": message_id, "data": fields[b"data"]},
            maxlen=10000,
            approximate=True,
        )
        self.clear_attempts(stream, message_id)

    def increment_attempts(self, stream: str, message_id: bytes) -> int:
        if self.client is None:
            raise RuntimeError("Redis client not initialized")
        return self.client.hincrby(f"{stream}{DEAD_LETTER_SUFFIX}:attempts", message_id, 1)

    def clear_attempts(self, stream: str, message_id: bytes) -> None:
        if self.client is None:
            raise RuntimeError("Redis client not initialized")
        self.client.hdel(f"{stream}{DEAD_LETTER_SUFFIX}:attempts", message_id)

    def process_message(self, message: dict[str, Any]) -> None:
        data = message.get("data")
        if not isinstance(data, dict):
            logger.warning("Received sensor update message without a dict data payload")
            return
        sensor_id = data.get("sensor_id")
        timestamp = message.get("timestamp")
        if not any((sensor_id, data, timestamp)):
            logger.warning("Received sensor update message without a valid payload")
            return

        temp = data.get("temp")
        humidity = data.get("humidity")
        created_at = datetime.fromisoformat(timestamp) if timestamp else timezone.now()
        SensorLog.objects.create(sensor_id=sensor_id, temp=temp, humidity=humidity, created_at=created_at)

        logger.info(
            f"Created SensorLog for sensor {sensor_id}: temp={temp}, humidity={humidity}, created_at={created_at}"
        )

    def signal_handler(self, signum: int, frame: Any) -> None:
        logger.info("\nShutting down consumer...")
        self.running = False

    def cleanup(self) -> None:
        self.client = None
        logger.info("Consumer closed.")
