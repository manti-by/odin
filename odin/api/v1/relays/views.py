from django.db.models import query
from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet

from odin.api.v1.relays.serializers import RelaySerializer, RelayUpdateSerializer
from odin.apps.relays.models import Relay


class RelaysView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = RelaySerializer

    def get_queryset(self) -> query.QuerySet:
        return Relay.objects.active()


class RelayUpdateView(mixins.UpdateModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = RelayUpdateSerializer
    queryset = Relay.objects.all()

    lookup_field = "relay_id"
    lookup_url_kwarg = "relay_id"

    def perform_update(self, serializer: RelayUpdateSerializer) -> None:
        serializer.instance.context.update(**serializer.validated_data["context"])
        serializer.instance.save(update_fields=["context"])
