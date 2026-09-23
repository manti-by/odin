from django.urls import path

from odin.api.v1.provider.views import TrafficCurrentView


app_name = "provider"


urlpatterns = [
    path("traffic/", TrafficCurrentView.as_view(), name="traffic"),
]
