from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.utils import timezone

from odin.apps.weather.models import Weather


VAPOR_PRESSURE_BASE = Decimal("6.105")
VAPOR_PRESSURE_SCALE = Decimal("17.27")
VAPOR_PRESSURE_OFFSET = Decimal("237.7")

WEATHER_MAX_AGE = timedelta(hours=2)


def get_latest_weather(max_age: timedelta = WEATHER_MAX_AGE) -> Weather | None:
    """Return the weather row that can drive the heating rules right now, or None.

    `Weather.objects.current()` falls back to the last row regardless of age and, having no
    ordering, to the highest pk — which can be a forecast slot in the future. A row only counts as
    usable when it carries a temperature, its `period` sits within `max_age` of now in either
    direction and the provider wrote it (`synced_at`) within the last `max_age`, so a dead feed
    cannot pin the last band forever. Eligible rows are filtered before one is picked, so neither a
    far-ahead forecast nor a row without a temperature can shadow a usable earlier row; the most
    recent started row wins, then the nearest upcoming one.

    Args:
        max_age: maximum distance between now and both timestamps.

    Returns:
        The current Weather row, or None when there is no fresh one.
    """
    now = timezone.now()
    # `#>>` yields NULL for a JSON null, unlike a plain `data__temp__avg__isnull` key transform
    temperature = KeyTextTransform("avg", KeyTransform("temp", "data"))
    usable = Weather.objects.alias(temperature=temperature).filter(
        temperature__isnull=False,
        period__range=(now - max_age, now + max_age),
        synced_at__gte=now - max_age,
    )
    return usable.filter(period__lte=now).order_by("-period").first() or usable.order_by("period").first()


def apparent_temp(temp: Decimal | None, humidity: Decimal | None, wind_speed: Decimal | None) -> Decimal | None:
    """Steadman apparent temperature, combining dry-bulb temp, relative humidity and wind.

    Args:
        temp: air temperature in °C.
        humidity: relative humidity in %.
        wind_speed: mean wind speed in m/s.

    Returns:
        The apparent temperature in °C, or None when any input is missing so the caller can
        fall back to the raw temperature.
    """
    if temp is None or humidity is None or wind_speed is None:
        return None

    vapor_pressure = (
        humidity / 100 * VAPOR_PRESSURE_BASE * (VAPOR_PRESSURE_SCALE * temp / (VAPOR_PRESSURE_OFFSET + temp)).exp()
    )
    return temp + Decimal("0.33") * vapor_pressure - Decimal("0.70") * wind_speed - Decimal("4.00")


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
        except KeyError, TypeError, ValueError:
            temp.append(None)

        try:
            humidity.append(float(entry.data["humidity"]))
        except KeyError, TypeError, ValueError:
            humidity.append(None)

        try:
            pressure.append(int(entry.data["pressure"]))
        except KeyError, TypeError, ValueError:
            pressure.append(None)

    return {
        "timestamps": timestamps,
        "temp": temp,
        "humidity": humidity,
        "pressure": pressure,
    }
