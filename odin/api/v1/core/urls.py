from django.urls import path

from odin.api.v1.core.views import (
    ApplicationServerKeyView,
    ChartView,
    CsrfTokenView,
    DeviceView,
    HealthCheckView,
    SystemdStatusView,
    WeatherChartView,
)
from odin.api.v1.logs.views import LogsView


app_name = "core"


urlpatterns = [
    path("chart/", ChartView.as_view(), name="chart"),
    path("weather-chart/", WeatherChartView.as_view(), name="weather-chart"),
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
    path("devices/", DeviceView.as_view(), name="devices"),
    path("systemd/", SystemdStatusView.as_view(), name="systemd"),
    # Deprecated alias: external log forwarders still POST to the old core/logs/ URL.
    # Kept mapped to the same view (not a redirect, which would drop the POST body)
    # during the transition to logs/. Remove once satellites are updated.
    path("logs/", LogsView.as_view(), name="logs"),
    path("app-server-key/", ApplicationServerKeyView.as_view(), name="app-server-key"),
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
]
