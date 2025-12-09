from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class LogSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    msg = serializers.CharField(max_length=100)
    filename = serializers.CharField(max_length=100)
    levelname = serializers.CharField(max_length=100)
    asctime = serializers.DateTimeField()


class MetricChoices(TextChoices):
    TEMP = "temp", _("Temp")
    HUMIDITY = "humidity", _("Humidity")
    PRESSURE = "pressure", _("Pressure")


class ChartTypeSerializer(serializers.Serializer):
    value = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        allow_null=False,
    )
    metric = serializers.ChoiceField(choices=MetricChoices.choices)
