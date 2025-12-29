from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def chart_view(request: HttpRequest) -> HttpResponse:
    """View for DS18B20 temperature chart page."""
    return render(request, "chart.html")
