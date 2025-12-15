from django.urls import path

from odin.api.v1.sensors.views import SensorsLogView, SensorsUpdateView, SensorsView


app_name = "sensors"


urlpatterns = [
    path("", SensorsView.as_view({"get": "list"}), name="list"),
    path("logs/", SensorsLogView.as_view({"get": "list", "post": "create"}), name="logs"),
    path("<str:sensor_id>/", SensorsUpdateView.as_view({"patch": "partial_update"}), name="update"),
]
