from django.urls import path

from odin.api.v1.sensors.views import (
    DS18B20DataView,
    SensorsLogView,
    SensorsUpdateView,
    SensorsView,
)


app_name = "sensors"


urlpatterns = [
    path("", SensorsView.as_view({"get": "list"}), name="list"),
    path("logs/", SensorsLogView.as_view({"get": "list", "post": "create"}), name="logs"),
    path("ds18b20/", DS18B20DataView.as_view(), name="ds18b20"),
    path("<str:sensor_id>/", SensorsUpdateView.as_view({"patch": "partial_update"}), name="update"),
]
