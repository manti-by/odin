from typing import Any

from django.core.cache import cache

from odin.apps.core.models import Log
from odin.apps.electricity.models import VoltageLog
from odin.apps.sensors.models import Sensor
from odin.apps.weather.models import Weather


INDEX_CONTEXT_CACHE_KEY = "index_context"
INDEX_CONTEXT_CACHE_TIMEOUT = 120


def build_index_context() -> dict[str, Any]:
    voltage = VoltageLog.objects.order_by("created_at").last()
    home_sensors_is_alive = all([x.is_alive for x in Sensor.objects.active().ds18b20()])
    boiler_sensors_is_alive = all([x.is_alive for x in Sensor.objects.active().esp8266()])
    weather = Weather.objects.current()
    sensors = Sensor.objects.active().visible().order_by("order")
    error_logs = Log.objects.errors_last_day()

    return {
        "weather": weather,
        "sensors": sensors,
        "home_sensors_is_alive": home_sensors_is_alive,
        "boiler_sensors_is_alive": boiler_sensors_is_alive,
        "error_logs": error_logs,
        "voltage": voltage,
    }


def get_cached_index_context() -> dict[str, Any] | None:
    return cache.get(INDEX_CONTEXT_CACHE_KEY)


def set_cached_index_context(context: dict[str, Any]) -> None:
    cache.set(INDEX_CONTEXT_CACHE_KEY, context, INDEX_CONTEXT_CACHE_TIMEOUT)


def update_index_context_cache() -> dict:
    context = build_index_context()
    set_cached_index_context(context)
    return context
