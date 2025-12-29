from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def ds18b20_chart_view(request: HttpRequest) -> HttpResponse:
    """View for DS18B20 temperature chart page."""
    return render(request, "ds18b20.html")
