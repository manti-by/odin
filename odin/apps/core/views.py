import logging

from django.http import HttpRequest
from django.shortcuts import render
from django.utils import timezone

from odin.apps.weather.models import Weather


logger = logging.getLogger(__name__)


def index_view(request: HttpRequest) -> str:
    context = {
        "time": timezone.now().strftime("%d %b %Y %H:%m"),
        "weather": Weather.objects.current(),
    }
    return render(request, "index.html", context=context)
