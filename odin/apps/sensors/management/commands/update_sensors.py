import logging

import requests
from django.core.management import BaseCommand
from django.utils import timezone

from ...models import Sensor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = description = "Retrieve the data from Coruscant server."
    url = "http://coruscant.local/batch/"

    def handle(self, *args, **options):
        limit = 500
        offset = 0
        created_exists = True
        current_tz = timezone.get_current_timezone()
        while created_exists:
            response = requests.get(f"{self.url}?limit={limit}&offset={offset}")
            if response.ok:
                for sensor in response.json():
                    sensor["created_at"] = current_tz.localize(sensor["created_at"])
                    _, created = Sensor.objects.get_or_create(external_id=sensor.pop("id"), defaults=sensor)
                    created_exists = created or False
                offset += limit
