from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer


class RelaySerializer(BaseSerializer):
    relay_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    context = serializers.JSONField()
    created_at = serializers.DateTimeField(read_only=True)


class RelayUpdateContextSerializer(BaseSerializer):
    state = serializers.CharField()


class RelayUpdateSerializer(BaseSerializer):
    context = RelayUpdateContextSerializer()

    @property
    def data(self) -> dict:
        """Ad-hoc solution to prevent response rendering errors."""
        return self.validated_data
