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
        if "context" in serializer.validated_data:
            serializer.instance.context.update(**serializer.validated_data["context"])
            serializer.instance.save(update_fields=["context"])
        if "force_state" in serializer.validated_data:
            serializer.instance.force_state = serializer.validated_data["force_state"]
            serializer.instance.save(update_fields=["force_state"])
