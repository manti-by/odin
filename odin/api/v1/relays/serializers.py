from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer


class RelaySerializer(BaseSerializer):
    relay_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    context = serializers.JSONField()
    created_at = serializers.DateTimeField(read_only=True)
