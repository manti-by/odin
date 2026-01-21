from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


def chart_view(request: HttpRequest, title: str, container_class: str, api_url: str, sensor_type: str) -> HttpResponse:
    return render(
        request,
        "chart.html",
        {"title": title, "container_class": container_class, "api_url": api_url, "sensor_type": sensor_type},
    )


def chart_boiler_view(request: HttpRequest) -> HttpResponse:
    title: str = _("Boiler Temperatures")  # noqa
    return chart_view(request, title, "ds18b20", "api:v1:sensors:ds18b20", "DS18B20")


def chart_home_view(request: HttpRequest) -> HttpResponse:
    title: str = _("Home Temperatures")  # noqa
    return chart_view(request, title, "esp8266", "api:v1:sensors:esp8266", "ESP8266")
