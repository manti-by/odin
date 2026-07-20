from typing import Any

from rest_framework import mixins
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import GenericViewSet

from odin.api.authentication import TokenAuthentication
from odin.api.v1.relays.serializers import RelaySerializer, RelayUpdateSerializer
from odin.apps.relays.models import Relay


class RelaysBaseView(GenericViewSet):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    queryset = Relay.objects.active()
    lookup_field = "relay_id"
    lookup_url_kwarg = "relay_id"


class RelaysView(mixins.ListModelMixin, RelaysBaseView):
    permission_classes = (AllowAny,)
    serializer_class = RelaySerializer


class RelayRetrieveUpdateView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, RelaysBaseView):
    throttle_scope = "relays_update"
    serializer_class = RelayUpdateSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RelaySerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return (IsAuthenticated(),)
        return (AllowAny(),)

    def get_throttles(self):
        if self.action in ("update", "partial_update"):
            return (ScopedRateThrottle(),)
        return ()

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
