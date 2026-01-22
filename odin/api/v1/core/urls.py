from django.urls import path

from odin.api.v1.core.views import ApplicationServerKeyView, ChartView, DeviceView, HealthCheckView, LogsView


app_name = "core"


urlpatterns = [
    path("logs/", LogsView.as_view(), name="logs"),
    path("chart/", ChartView.as_view(), name="chart"),
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
    path("devices/", DeviceView.as_view(), name="devices"),
    path("app-server-key/", ApplicationServerKeyView.as_view(), name="app-server-key"),
]
