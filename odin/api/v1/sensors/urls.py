from django.urls import path

from odin.api.v1.sensors.views import SensorsLogView, SensorsView


app_name = "sensors"


urlpatterns = [
    path("", SensorsView.as_view(), name="sensors"),
    path("logs/", SensorsLogView.as_view(), name="logs"),
]
