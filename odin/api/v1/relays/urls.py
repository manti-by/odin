from django.urls import path

from odin.api.v1.relays.views import RelaysView


app_name = "relays"


urlpatterns = [
    path("", RelaysView.as_view({"get": "list"}), name="list"),
]
