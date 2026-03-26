import logging
import signal
import sys
from datetime import datetime

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from command_log.management.commands import LoggedCommand
from django.conf import settings
from django.utils import timezone

from odin.apps.core.kafka import KafkaService, MessageType
from odin.apps.sensors.models import SensorLog


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = "Runs a Kafka consumer to listen for sensor data updates."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True
        self.consumer: KafkaConsumer | None = None

    def handle(self, *args, **options):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("Starting Kafka sensor consumer...")
        self.consumer = KafkaService.get_consumer()
        self.consumer.subscribe([settings.KAFKA_ODIN_TOPIC])
        logger.info(f"Subscribed to topic: {settings.KAFKA_ODIN_TOPIC}")

        try:
            while self.running:
                records = self.consumer.poll(timeout_ms=1000)
                for _, messages in records.items():
                    for message in messages:
                        if not self.running:
                            break
                        if message.value and message.value.get("type") == MessageType.SENSOR_DATA_UPDATE.value:
                            self.process_message(message=message.value)

        except KafkaError as e:
            self.stderr.write(f"Kafka error: {e}")
            sys.exit(1)
        finally:
            self.cleanup()

    def process_message(self, message: dict) -> None:
        data = message.get("data", {})
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

    def signal_handler(self, signum, frame):
        logger.info("\nShutting down consumer...")
        self.running = False

    def cleanup(self):
        if self.consumer:
            self.consumer.close()
            self.consumer = None
        logger.info("Consumer closed.")
