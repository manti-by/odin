from __future__ import annotations

from typing import Any

from rest_framework import serializers


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
