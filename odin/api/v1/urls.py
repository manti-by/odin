from django.urls import include, path


app_name = "v1"


urlpatterns = [
    path("core/", include("odin.api.v1.core.urls"), name="core"),
    path("relays/", include("odin.api.v1.relays.urls"), name="relays"),
    path("sensors/", include("odin.api.v1.sensors.urls"), name="sensors"),
]
