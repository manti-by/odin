import logging

import requests
from command_log.management.commands import LoggedCommand
from dateutil import parser

from odin.apps.sensors.models import Sensor, SyncLog

logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Retrieve the data from Coruscant server."
    url = "http://coruscant.local/batch/"

    offset = 0
    limit = 500
    timeout = 30

    def handle(self, *args, **options):
        created_exists = True
        while created_exists:
            try:
                response = requests.get(f"{self.url}?limit={self.limit}&offset={self.offset}", timeout=self.timeout)
            except ConnectionError as e:
                logger.error(f"Error retrieving data from Coruscant server: {e}")
                break

            if response.ok:
                for sensor in response.json():
                    sensor["created_at"] = parser.parse(sensor["created_at"])
                    _, created = Sensor.objects.get_or_create(external_id=sensor.pop("id"), defaults=sensor)
                    SyncLog.objects.create(type="IN", synced_count=created)
                    created_exists = created or False
                self.offset += self.limit
