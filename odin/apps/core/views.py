import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from odin.apps.sensors.models import Sensor
from odin.apps.weather.models import Weather


logger = logging.getLogger(__name__)


def index_view(request: HttpRequest) -> HttpResponse:
    context = {
        "time": timezone.localtime(timezone.now()).strftime("%d %b %Y %H:%m"),
        "weather": Weather.objects.current(),
        "sensors": Sensor.objects.active().order_by("-created_at", "name"),
    }
    return render(request, "index.html", context=context)
