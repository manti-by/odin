from django.urls import path

from odin.api.v1.core.views import ChartView, HealthCheckView


app_name = "core"


urlpatterns = [
    path("chart/", ChartView.as_view(), name="chart"),
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
]
