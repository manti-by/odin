from django.urls import path

from odin.apps.sensors.views import ds18b20_chart_view


app_name = "sensors"


urlpatterns = [
    path("", ds18b20_chart_view, name="ds18b20_chart"),
]
