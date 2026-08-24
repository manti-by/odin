from __future__ import annotations

import json
import logging
import signal
import sys
from datetime import datetime
from typing import Any

from redis.exceptions import RedisError

from command_log.management.commands import LoggedCommand
from django.conf import settings
from django.db.utils import DatabaseError
from django.utils import timezone

from odin.apps.core.redis_bus import MessageType, RedisBus
from odin.apps.sensors.models import SensorLog


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = "Runs a Redis pub/sub consumer to listen for sensor data updates."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.running: bool = True
        self.client: Any | None = None
        self.pubsub: Any | None = None

    def handle(self, *args: Any, **options: Any) -> None:
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("Starting Redis sensor consumer...")
        self.client = RedisBus.get_redis()
        channel = settings.REDIS_SENSORS_CHANNEL
        self.pubsub = self.client.pubsub()
        self.pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel}")

        try:
            for message in self.pubsub.listen():
                if not self.running:
                    break
                if message.get("type") != "message":
                    continue
                self.process_message(message.get("data"))

        except (RedisError, OSError) as e:
            self.stderr.write(f"Redis error: {e}")
            sys.exit(1)
        finally:
            self.cleanup()

    def process_message(self, raw: Any) -> None:
        try:
            message = json.loads(raw)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Skipping malformed sensor message: {e}")
            return
        if not isinstance(message, dict):
            logger.warning("Skipping sensor message with non-dict payload")
            return
        if message.get("type") != MessageType.SENSOR_DATA_UPDATE.value:
            logger.warning(f"Skipping sensor message with unexpected type {message.get('type')!r}")
            return
        try:
            self.process_envelope(message=message)
        except (ValueError, TypeError, AttributeError, DatabaseError) as e:
            logger.error(f"Failed to process sensor message: {e}")

    def process_envelope(self, message: dict[str, Any]) -> None:
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
        if self.pubsub is not None:
            try:
                self.pubsub.unsubscribe()
                self.pubsub.close()
            except RedisError as e:
                logger.error(f"Error closing pubsub: {e}")
        self.pubsub = None
        self.client = None
        logger.info("Consumer closed.")
