from django.urls import path

from odin.api.v1.sensors.views import (
    ChartOptionsView,
    DS18B20DashboardView,
    DS18B20DataView,
    ESP8266DashboardView,
    ESP8266DataView,
    SensorsLogView,
    SensorsUpdateView,
    SensorsView,
)


app_name = "sensors"


urlpatterns = [
    path("", SensorsView.as_view({"get": "list"}), name="list"),
    path("logs/", SensorsLogView.as_view({"get": "list", "post": "create"}), name="logs"),
    path("ds18b20/", DS18B20DataView.as_view(), name="ds18b20"),
    path("ds18b20/dashboard/", DS18B20DashboardView.as_view(), name="ds18b20-dashboard"),
    path("esp8266/", ESP8266DataView.as_view(), name="esp8266"),
    path("esp8266/dashboard/", ESP8266DashboardView.as_view(), name="esp8266-dashboard"),
    path("chart-options/", ChartOptionsView.as_view(), name="chart-options"),
    path("<str:sensor_id>/", SensorsUpdateView.as_view({"patch": "partial_update"}), name="update"),
]
