from django.urls import path

from odin.api.v1.core.views import ChartView, DeviceView, HealthCheckView, LogsView, VapidPublicKeyView


app_name = "core"


urlpatterns = [
    path("logs/", LogsView.as_view(), name="logs"),
    path("chart/", ChartView.as_view(), name="chart"),
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
    path("devices/", DeviceView.as_view(), name="devices"),
    path("vapid/", VapidPublicKeyView.as_view(), name="vapid"),
]
