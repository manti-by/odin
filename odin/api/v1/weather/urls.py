from django.urls import path

from odin.api.v1.weather.views import WeatherCurrentView


app_name = "weather"


urlpatterns = [
    path("current/", WeatherCurrentView.as_view(), name="current"),
]
