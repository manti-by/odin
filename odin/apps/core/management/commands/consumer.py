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
from django.utils.translation import gettext_lazy as _

from odin.apps.core.redis_bus import MessageType, RedisBus
from odin.apps.relays.models import Relay
from odin.apps.sensors.models import Sensor, SensorLog


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = _("Runs a Redis pub/sub consumer to listen for sensor and relay updates.")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize consumer state.

        Sets the running flag and prepares client/pubsub attributes so they are
        always available for the cleanup path.
        """
        super().__init__(*args, **kwargs)
        self.running: bool = True
        self.client: Any | None = None
        self.pubsub: Any | None = None

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the pub/sub consumer until a shutdown signal arrives.

        Subscribes to the sensor and relay channels and polls for messages on a
        bounded timeout so the loop can observe ``self.running`` during quiet
        periods. Redis setup and the receive loop share the same error path,
        and cleanup always runs.
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("Starting Redis consumer...")
        try:
            self.client = RedisBus.get_redis()
            channels = (settings.REDIS_SENSORS_CHANNEL, settings.REDIS_RELAYS_CHANNEL)
            self.pubsub = self.client.pubsub()
            self.pubsub.subscribe(*channels)
            logger.info(f"Subscribed to channels: {', '.join(channels)}")

            while self.running:
                message = self.pubsub.get_message(timeout=settings.REDIS_SOCKET_TIMEOUT)
                if message is None or message.get("type") != "message":
                    continue
                self.process_message(message.get("data"))

        except (RedisError, OSError, ValueError) as e:
            self.stderr.write(f"Redis error: {e}")
            sys.exit(1)
        finally:
            self.cleanup()

    def process_message(self, raw: Any) -> None:
        """Decode, validate, and dispatch a raw pub/sub message.

        Decodes the JSON envelope and routes it by ``type``. Malformed or
        unknown messages are skipped so the consumer tolerates new envelope
        types and duplicate deliveries.
        """
        try:
            message = json.loads(raw)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Skipping malformed bus message: {e}")
            return
        if not isinstance(message, dict):
            logger.warning("Skipping bus message with non-dict payload")
            return

        match message.get("type"):
            case MessageType.SENSOR_DATA_UPDATE.value:
                self.process_sensor_message(message)
            case MessageType.RELAY_STATE_UPDATE.value:
                self.process_relay_message(message)
            case other:
                logger.warning(f"Skipping bus message with unexpected type {other!r}")

    def process_sensor_message(self, message: dict[str, Any]) -> None:
        """Validate and persist a sensor data update message."""
        data = message.get("data")
        timestamp = message.get("timestamp")
        if not isinstance(data, dict) or not data.get("sensor_id") or not isinstance(timestamp, str):
            logger.warning("Skipping sensor message with missing required fields")
            return

        try:
            self.process_envelope(message=message)
        except (ValueError, TypeError, AttributeError, DatabaseError) as e:
            logger.error(f"Failed to process sensor message: {e}")

    def process_relay_message(self, message: dict[str, Any]) -> None:
        """Refresh a relay from its persisted state when a relay update arrives.

        The persisted ``relays:state:<relay_id>`` key written by Coruscant is
        the source of truth, so the message is treated as a wake-up signal and
        duplicates (including ODIN's own control echoes) are harmless. Unknown
        relay ids are ignored.
        """
        data = message.get("data")
        relay_id = data.get("relay_id") if isinstance(data, dict) else None
        if not relay_id:
            logger.warning("Skipping relay message with missing relay_id")
            return

        relay = Relay.objects.filter(relay_id=relay_id).first()
        if relay is None:
            logger.warning(f"Skipping relay message for unknown relay {relay_id!r}")
            return

        relay.refresh_state()

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

        if sensor := Sensor.objects.filter(sensor_id=sensor_id).order_by("created_at").last():
            sensor.update(temp=temp, humidity=humidity)
        SensorLog.objects.create(sensor=sensor, temp=temp, humidity=humidity, created_at=created_at)

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
