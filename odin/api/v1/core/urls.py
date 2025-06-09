from django.urls import path

from odin.api.v1.core.views import HealthCheckView


app_name = "core"


urlpatterns = [
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
]
