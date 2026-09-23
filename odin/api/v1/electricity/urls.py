from django.urls import path

from odin.api.v1.electricity.views import VoltageCurrentView


app_name = "electricity"


urlpatterns = [
    path("voltage/", VoltageCurrentView.as_view(), name="voltage"),
]
