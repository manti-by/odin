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

        t_avg = entry.data.get("temp")
        if t_avg is not None and t_avg.get("avg") is not None:
            temp.append(float(t_avg["avg"]))
        else:
            temp.append(None)

        h = entry.data.get("humidity")
        if h is not None:
            humidity.append(float(h))
        else:
            humidity.append(None)

        p = entry.data.get("pressure")
        if p is not None:
            pressure.append(int(p))
        else:
            pressure.append(None)

    return {
        "timestamps": timestamps,
        "temp": temp,
        "humidity": humidity,
        "pressure": pressure,
    }
