from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from odin.apps.core.models import Log
from odin.apps.electricity.models import VoltageLog
from odin.apps.sensors.models import Sensor
from odin.apps.weather.models import Weather


logger = logging.getLogger(__name__)


def index_view(request: HttpRequest) -> HttpResponse:
    voltage = VoltageLog.objects.last()
    home_sensors_is_alive = all([x.is_alive for x in Sensor.objects.active().ds18b20()])
    boiler_sensors_is_alive = all([x.is_alive for x in Sensor.objects.active().esp8266()])
    context = {
        "time": timezone.now().strftime("%d %b %Y %H:%M"),
        "weather": Weather.objects.current(),
        "sensors": Sensor.objects.active().visible().order_by("order"),
        "home_sensors_is_alive": home_sensors_is_alive,
        "boiler_sensors_is_alive": boiler_sensors_is_alive,
        "error_logs": Log.objects.errors_last_day(),
        "voltage": voltage,
    }
    return render(request, "index.html", context=context)
