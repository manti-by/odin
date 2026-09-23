from django.urls import include, path


app_name = "v1"


urlpatterns = [
    path("boiler/", include("odin.api.v1.boiler.urls"), name="boiler"),
    path("core/", include("odin.api.v1.core.urls"), name="core"),
    path("currency/", include("odin.api.v1.currency.urls"), name="currency"),
    path("electricity/", include("odin.api.v1.electricity.urls"), name="electricity"),
    path("logs/", include("odin.api.v1.logs.urls"), name="logs"),
    path("provider/", include("odin.api.v1.provider.urls"), name="provider"),
    path("relays/", include("odin.api.v1.relays.urls"), name="relays"),
    path("sensors/", include("odin.api.v1.sensors.urls"), name="sensors"),
    path("weather/", include("odin.api.v1.weather.urls"), name="weather"),
]
