from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone

from odin.apps.weather.models import Weather


VAPOR_PRESSURE_BASE = Decimal("6.105")
VAPOR_PRESSURE_SCALE = Decimal("17.27")
VAPOR_PRESSURE_OFFSET = Decimal("237.7")


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
