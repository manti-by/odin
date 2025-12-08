from django.urls import path

from odin.api.v1.core.views import ChartView, HealthCheckView, LogsView


app_name = "core"


urlpatterns = [
    path("logs/", LogsView.as_view(), name="logs"),
    path("chart/", ChartView.as_view(), name="chart"),
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
]
