from typing import Any

from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from odin.api.v1.relays.serializers import RelaySerializer, RelayUpdateSerializer
from odin.apps.relays.models import Relay


class RelaysBaseView(GenericViewSet):
    queryset = Relay.objects.active()
    lookup_field = "relay_id"
    lookup_url_kwarg = "relay_id"


class RelaysView(mixins.ListModelMixin, RelaysBaseView):
    serializer_class = RelaySerializer


class RelayRetrieveUpdateView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, RelaysBaseView):
    serializer_class = RelayUpdateSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RelaySerializer
        return self.serializer_class

    def perform_update(self, serializer: RelayUpdateSerializer) -> None:
        data: dict[str, Any] = serializer.validated_data
        if not serializer.instance:
            raise ValueError("Relay instance not found")

        update_fields = []
        item: Relay = serializer.instance
        if item and "context" in data:
            item.context.update(**data["context"])
            update_fields.append("context")

        if "force_state" in data:
            item.force_state = data["force_state"]
            update_fields.append("force_state")

        if update_fields:
            item.save(update_fields=update_fields)
