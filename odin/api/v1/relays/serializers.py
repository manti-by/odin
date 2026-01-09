from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer
from odin.apps.relays.models import RelayState


class RelaySerializer(BaseSerializer):
    relay_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    state = serializers.CharField()
    target_state = serializers.ChoiceField(choices=RelayState.choices)
    context = serializers.JSONField()
    force_state = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class RelayUpdateContextSerializer(BaseSerializer):
    state = serializers.CharField()


class RelayUpdateSerializer(BaseSerializer):
    context = RelayUpdateContextSerializer(required=False)
    force_state = serializers.CharField(required=False, allow_null=True)

    @property
    def data(self) -> dict:
        """Ad-hoc solution to prevent response rendering errors."""
        return self.validated_data
