from django.urls import path

from odin.api.v1.boiler.views import BoilerStatusView


app_name = "boiler"


urlpatterns = [
    path("status/", BoilerStatusView.as_view(), name="status"),
]
