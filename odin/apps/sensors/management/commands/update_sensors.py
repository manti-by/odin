import logging

import requests
from django.core.management import BaseCommand
from dateutil import parser

from odin.apps.sensors.models import Sensor, SyncLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = description = "Retrieve the data from Coruscant server."
    url = "http://coruscant.local/batch/"

    def handle(self, *args, **options):
        limit = 500
        offset = 0
        created_exists = True
        while created_exists:
            response = requests.get(f"{self.url}?limit={limit}&offset={offset}")
            if response.ok:
                for sensor in response.json():
                    sensor["created_at"] = parser.parse(sensor["created_at"])
                    _, created = Sensor.objects.get_or_create(external_id=sensor.pop("id"), defaults=sensor)
                    SyncLog.objects.create(type="IN", synced_count=created)
                    created_exists = created or False
                offset += limit
