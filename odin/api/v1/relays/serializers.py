from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer
from odin.apps.relays.models import Relay
from odin.apps.relays.services import RelayTargetStateService


class RelaySerializer(BaseSerializer):
    relay_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    state = serializers.CharField()
    mode = serializers.CharField()
    target_state = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_target_state(self, obj: Relay) -> str:
        state, _ = RelayTargetStateService(obj).get_target_state()
        return str(state)


class RelayUpdateContextSerializer(BaseSerializer):
    state = serializers.CharField()


class RelayUpdateSerializer(BaseSerializer):
    context = RelayUpdateContextSerializer(required=False)

    @property
    def data(self) -> dict:
        """Ad-hoc solution to prevent response rendering errors."""
        return self.validated_data
