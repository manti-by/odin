from django.utils import timezone
from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer


class SensorSerializer(BaseSerializer):
    sensor_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    context = serializers.JSONField()

    temp = serializers.DecimalField(max_digits=7, decimal_places=2)
    humidity = serializers.DecimalField(max_digits=7, decimal_places=2)
    temp_offset = serializers.DecimalField(max_digits=7, decimal_places=2)
    humidity_offset = serializers.DecimalField(max_digits=7, decimal_places=2)

    created_at = serializers.DateTimeField(read_only=True)


class SensorUpdateContextSerializer(BaseSerializer):
    target_temp = serializers.CharField()


class SensorUpdateSerializer(BaseSerializer):
    context = SensorUpdateContextSerializer(required=False)

    @property
    def data(self) -> dict:
        """Ad-hoc solution to prevent response rendering errors."""
        return self.validated_data


class SensorLogSerializer(BaseSerializer):
    sensor_id = serializers.CharField(max_length=32)
    temp = serializers.DecimalField(max_digits=5, decimal_places=2)
    humidity = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    created_at = serializers.DateTimeField(allow_null=True, required=False)

    def validate(self, data: dict) -> dict:
        if not data.get("created_at"):
            data["created_at"] = timezone.now()
        return data


class ChartQueryParamsSerializer(BaseSerializer):
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)


class ChartOptionsQueryParamsSerializer(BaseSerializer):
    type = serializers.ChoiceField(choices=["ds18b20", "esp8266"])
