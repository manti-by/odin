from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer


class SensorSerializer(BaseSerializer):
    sensor_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    context = serializers.JSONField()
    created_at = serializers.DateTimeField(read_only=True)


class SensorLogSerializer(BaseSerializer):
    sensor_id = serializers.CharField(max_length=32)
    temp = serializers.DecimalField(max_digits=5, decimal_places=2)
    humidity = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    created_at = serializers.DateTimeField()
