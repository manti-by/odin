import logging
import subprocess  # nosec
from typing import Any

from django.conf import settings
from django.core.cache import cache

from odin.apps.core.models import Log
from odin.apps.currency.models import ExchangeRate
from odin.apps.electricity.models import VoltageLog
from odin.apps.provider.models import Traffic
from odin.apps.sensors.models import Sensor
from odin.apps.weather.models import Weather


logger = logging.getLogger(__name__)

INDEX_CONTEXT_CACHE_KEY = "index_context"
INDEX_CONTEXT_CACHE_TIMEOUT = 120


def build_index_context() -> dict[str, Any]:
    voltage = VoltageLog.objects.first()
    home_sensors_is_alive = all([x.is_alive for x in Sensor.objects.active().esp8266()])
    boiler_sensors_is_alive = all([x.is_alive for x in Sensor.objects.active().ds18b20()])
    weather = Weather.objects.current()
    sensors = Sensor.objects.active().visible().order_by("order")
    error_logs = Log.objects.errors_last_day()
    exchange_rates = ExchangeRate.objects.current()
    traffic = Traffic.objects.first()

    return {
        "weather": weather,
        "sensors": sensors,
        "home_sensors_is_alive": home_sensors_is_alive,
        "boiler_sensors_is_alive": boiler_sensors_is_alive,
        "error_logs": error_logs,
        "voltage": voltage,
        "exchange_rates": exchange_rates,
        "traffic": traffic,
        "systemd_status": systemd_status(),
    }


def get_cached_index_context() -> dict[str, Any] | None:
    return cache.get(INDEX_CONTEXT_CACHE_KEY)


def set_cached_index_context(context: dict[str, Any]) -> None:
    cache.set(INDEX_CONTEXT_CACHE_KEY, context, INDEX_CONTEXT_CACHE_TIMEOUT)


def update_index_context_cache() -> dict:
    context = build_index_context()
    set_cached_index_context(context)
    return context


def systemd_status() -> dict[str, dict]:
    if settings.DEBUG:
        return {"scheduler.service": {"status": "active"}, "worker.service": {"error": "DEBUG error message"}}

    result = {}
    for service in ["scheduler.service", "worker.service"]:
        try:
            status = subprocess.run(["/usr/bin/systemctl", "is-active", service], capture_output=True, check=True)  # nosec
            result[service] = {"status": status.stdout.decode().strip()}
        except subprocess.CalledProcessError as e:
            logger.error(f"Cannot get status for {service}: {e}")
            result[service] = {"error": str(e)}
    return result
