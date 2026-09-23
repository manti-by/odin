from typing import Any

from django.utils import timezone
from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer
from odin.apps.sensors.models import SensorType


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

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("created_at"):
            attrs["created_at"] = timezone.now()
        return attrs


class ChartQueryParamsSerializer(BaseSerializer):
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)


class ChartOptionsQueryParamsSerializer(BaseSerializer):
    type = serializers.ChoiceField(choices=SensorType.choices)


class DashboardRelaySerializer(serializers.Serializer):
    relay_id = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=32)
    type = serializers.CharField(max_length=32)
    state = serializers.CharField(max_length=32)
    mode = serializers.SerializerMethodField()
    is_on = serializers.BooleanField()

    def get_mode(self, obj: Any) -> str:
        _, mode = obj.get_target_state()
        return str(mode)


class LinkedSensorSerializer(serializers.Serializer):
    sensor_id = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=32)
    temp = serializers.DecimalField(max_digits=7, decimal_places=2, allow_null=True)


class DashboardSensorSerializer(serializers.Serializer):
    sensor_id = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=32)
    type = serializers.ChoiceField(choices=SensorType.choices)
    context = serializers.JSONField()
    temp = serializers.DecimalField(max_digits=7, decimal_places=2, allow_null=True)
    humidity = serializers.DecimalField(max_digits=7, decimal_places=2, allow_null=True)
    temp_offset = serializers.DecimalField(max_digits=7, decimal_places=2, allow_null=True)
    humidity_offset = serializers.DecimalField(max_digits=7, decimal_places=2, allow_null=True)
    created_at = serializers.DateTimeField()
    relay = serializers.SerializerMethodField()
    linked_sensor = serializers.SerializerMethodField()
    is_alive = serializers.BooleanField()

    def get_relay(self, obj: Any) -> dict | None:
        if obj.relay:
            return DashboardRelaySerializer(obj.relay).data
        return None

    def get_linked_sensor(self, obj: Any) -> dict | None:
        if obj.linked_sensor:
            return LinkedSensorSerializer(obj.linked_sensor).data
        return None


class DashboardSensorsSerializer(serializers.Serializer):
    is_alive = serializers.BooleanField()
    sensors = DashboardSensorSerializer(many=True)
