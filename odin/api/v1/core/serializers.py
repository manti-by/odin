from __future__ import annotations

from typing import Any

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer
from odin.apps.core.models import Browser
from odin.apps.sensors.models import SensorType


class DeviceSubscriptionSerializer(serializers.Serializer):
    subscription = serializers.JSONField()
    browser = serializers.ChoiceField(choices=Browser.choices, default=Browser.OTHER)


class LogSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    msg = serializers.CharField(max_length=100)
    filename = serializers.CharField(max_length=100)
    levelname = serializers.CharField(max_length=100)
    asctime = serializers.DateTimeField()
    stacktrace = serializers.JSONField(allow_null=True, required=False)
    variables = serializers.JSONField(allow_null=True, required=False)


class MetricChoices(TextChoices):
    TEMP = "temp", _("Temp")
    HUMIDITY = "humidity", _("Humidity")
    PRESSURE = "pressure", _("Pressure")
    VOLTAGE = "voltage", _("Voltage")


class ChartTypeSerializer(serializers.Serializer):
    value = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        max_value=1000,
        min_value=-50,
        allow_null=False,
    )
    metric = serializers.ChoiceField(choices=MetricChoices.choices)


class DashboardRelaySerializer(serializers.Serializer):
    relay_id = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=32)
    type = serializers.CharField(max_length=32)
    state = serializers.CharField(max_length=32)
    is_on = serializers.BooleanField()


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


class WeatherSerializer(serializers.Serializer):
    temp = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    temp_display = serializers.CharField(max_length=10)
    temp_min = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    temp_min_display = serializers.CharField(max_length=10)
    temp_max = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    temp_max_display = serializers.CharField(max_length=10)
    pressure = serializers.IntegerField(allow_null=True)
    humidity = serializers.SerializerMethodField()
    wind = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    has_attrs = serializers.BooleanField()
    period = serializers.DateTimeField()
    synced_at = serializers.DateTimeField()
    provider = serializers.CharField(max_length=32)

    def get_humidity(self, obj: Any) -> Any:
        return (obj.data or {}).get("humidity")

    def get_wind(self, obj: Any) -> dict:
        wind = (obj.data or {}).get("wind") or {}
        return {
            "direction": wind.get("direction"),
            "speed": wind.get("speed"),
            "gusts": wind.get("gusts"),
        }

    def get_attributes(self, obj: Any) -> dict[str, bool]:
        attrs = (obj.data or {}).get("attributes") or {}
        return {
            "fog": bool(attrs.get("fog")),
            "snow": bool(attrs.get("snow")),
            "thunderstorm": bool(attrs.get("thunderstorm")),
            "black_ice": bool(attrs.get("black_ice")),
        }


class ExchangeRateSerializer(serializers.Serializer):
    currency = serializers.CharField(max_length=3)
    rate = serializers.DecimalField(max_digits=10, decimal_places=4)
    rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=4)
    scale = serializers.IntegerField()
    date = serializers.DateField()


class TrafficSerializer(serializers.Serializer):
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.CharField(max_length=16)
    created_at = serializers.DateTimeField()


class VoltageSerializer(serializers.Serializer):
    voltage = serializers.DecimalField(max_digits=7, decimal_places=2)
    created_at = serializers.DateTimeField()


class ErrorLogSerializer(serializers.Serializer):
    asctime = serializers.DateTimeField()
    msg = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=100)
    levelname = serializers.CharField(max_length=100)
    filename = serializers.CharField(max_length=100)


class DashboardSerializer(serializers.Serializer):
    weather = WeatherSerializer(allow_null=True, required=False)
    sensors = serializers.SerializerMethodField()
    home_sensors_is_alive = serializers.BooleanField(default=False)
    boiler_sensors_is_alive = serializers.BooleanField(default=False)
    error_logs = ErrorLogSerializer(many=True, default=list)
    voltage = VoltageSerializer(allow_null=True, required=False)
    exchange_rates = ExchangeRateSerializer(many=True, default=list)
    exchange_rates_trends = serializers.JSONField(default=dict)
    systemd_status = serializers.JSONField(default=dict)
    traffic = TrafficSerializer(allow_null=True, required=False)

    def get_sensors(self, instance: dict) -> dict[str, list]:
        sensors_qs = instance.get("sensors") or []
        if not hasattr(sensors_qs, "__iter__"):
            sensors_qs = []

        esp8266 = []
        ds18b20 = []
        for sensor in sensors_qs:
            data = DashboardSensorSerializer(sensor).data
            if sensor.type == SensorType.ESP8266:
                esp8266.append(data)
            else:
                ds18b20.append(data)

        return {"esp8266": esp8266, "ds18b20": ds18b20}


class WeatherChartQueryParamsSerializer(BaseSerializer):
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
