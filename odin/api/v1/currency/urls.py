from django.urls import path

from odin.api.v1.currency.views import ExchangeRateCurrentView


app_name = "currency"


urlpatterns = [
    path("rates/", ExchangeRateCurrentView.as_view(), name="rates"),
]
