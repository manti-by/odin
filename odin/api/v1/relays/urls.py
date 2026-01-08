from django.urls import path

from odin.api.v1.relays.views import RelayRetrieveUpdateView, RelaysView


app_name = "relays"


urlpatterns = [
    path("", RelaysView.as_view({"get": "list"}), name="list"),
    path(
        "<str:relay_id>/",
        RelayRetrieveUpdateView.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="retrieve_update",
    ),
]
