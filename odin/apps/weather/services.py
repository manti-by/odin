from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone

from odin.apps.weather.models import Weather


def get_weather_chart_data(start: datetime | None = None, end: datetime | None = None) -> dict[str, Any]:
    end_dt = end or timezone.now()
    start_dt = start or (end_dt - timedelta(hours=48))

    entries = Weather.objects.filter(period__range=(start_dt, end_dt)).order_by("period")

    timestamps: list[str] = []
    temp: list[float | None] = []
    humidity: list[float | None] = []
    pressure: list[int | None] = []

    for entry in entries:
        timestamps.append(entry.period.isoformat())

        try:
            temp.append(float(entry.data["temp"]["avg"]))
        except (KeyError, TypeError, ValueError):
            temp.append(None)

        try:
            humidity.append(float(entry.data["humidity"]))
        except (KeyError, TypeError, ValueError):
            humidity.append(None)

        try:
            pressure.append(int(entry.data["pressure"]))
        except (KeyError, TypeError, ValueError):
            pressure.append(None)

    return {
        "timestamps": timestamps,
        "temp": temp,
        "humidity": humidity,
        "pressure": pressure,
    }
