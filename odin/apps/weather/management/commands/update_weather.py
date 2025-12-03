import logging
from datetime import datetime, timedelta

import requests

from command_log.management.commands import LoggedCommand

from odin.apps.weather.models import Weather


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Retrieve the data from Pogoda.by server."
    url = "https://pogoda.by/api/v2/numeric-weather/2/26852"

    @staticmethod
    def serialize(item: dict) -> dict:
        return {
            "temp": {
                "avg": item.get("TMP"),
                "min": item.get("TMP_MIN"),
                "max": item.get("TMP_MAX"),
            },
            "precipitation": item.get("PRECIP"),
            "humidity": item.get("RH"),
            "wind": {
                "speed": item.get("WINDSP"),
                "direction": item.get("WINDDIR"),
                "gusts": item.get("GUST"),
            },
            "pressure": item.get("PRESSURE"),
            "pressure_modification": item.get("PRESSURE_MODIF"),
            "attributes": {
                "snow": bool(item.get("SNOW")),
                "thunderstorm": bool(item.get("GROZA")),
                "black_ice": bool(item.get("GOLOLED")),
                "fog": bool(item.get("TUMAN")),
            },
        }

    def handle(self, *args, **options):
        response = requests.get(self.url, timeout=60).json()
        for_date = next(iter(response))
        for item in response[for_date].values():
            period = datetime.fromisoformat(item.get("DATES")) + timedelta(hours=item.get("ADVANCE_TIME", 0))
            external_id = f"{item.get('ID_WEATHER')}-{item.get('CITY_ID')}-{period.isoformat()}"
            serialized_data = self.serialize(item)
            Weather.objects.update_or_create(
                external_id=external_id,
                period=period,
                defaults={"data": serialized_data},
            )
            logger.info(f"{period} - {serialized_data['temp']} *C")
