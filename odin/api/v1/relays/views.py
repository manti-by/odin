from django.db.models import query
from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet

from odin.api.v1.relays.serializers import RelaySerializer
from odin.apps.relays.models import Relay


class RelaysView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = RelaySerializer

    def get_queryset(self) -> query.QuerySet:
        return Relay.objects.active()
