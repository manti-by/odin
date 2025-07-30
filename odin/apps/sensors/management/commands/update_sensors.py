import logging

from command_log.management.commands import LoggedCommand
from odin.apps.sensors.models import RawSensor, Sensor


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Convert raw sensors data."

    def handle(self, *args, **options):
        synced_count = 0
        for raw_sensor in RawSensor.objects.filter(is_synced=False).order_by("created_at"):
            Sensor.objects.create(external_id=raw_sensor.address, temp=raw_sensor.temp)
            synced_count += 1
            raw_sensor.is_synced = True
            raw_sensor.save()
        return synced_count
