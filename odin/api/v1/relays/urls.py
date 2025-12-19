from django.urls import path

from odin.api.v1.relays.views import RelaysView, RelayUpdateView


app_name = "relays"


urlpatterns = [
    path("", RelaysView.as_view({"get": "list"}), name="list"),
    path("<str:relay_id>/", RelayUpdateView.as_view({"patch": "partial_update"}), name="update"),
]
