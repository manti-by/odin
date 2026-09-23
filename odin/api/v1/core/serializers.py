from __future__ import annotations

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer
from odin.apps.core.models import Browser


class DeviceSubscriptionSerializer(serializers.Serializer):
    subscription = serializers.JSONField()
    browser = serializers.ChoiceField(choices=Browser.choices, default=Browser.OTHER)


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


class WeatherChartQueryParamsSerializer(BaseSerializer):
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
