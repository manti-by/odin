from __future__ import annotations

from django.db import models
from django.db.models import query
from django.utils.translation import gettext_lazy as _


class SensorType(models.TextChoices):
    DS18B20 = "DS18B20"
    ESP8266 = "ESP8266"


class SensorQuerySet(query.QuerySet):
    pass


class SensorManager(models.Manager):
    def active(self) -> query.QuerySet:
        return self.get_queryset().filter(is_active=True).distinct("sensor_id")


class Sensor(models.Model):
    sensor_id = models.CharField(max_length=32)
    name = models.CharField(max_length=32)
    type = models.CharField(max_length=32, choices=SensorType.choices)
    is_active = models.BooleanField(default=True)
    context = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SensorManager.from_queryset(SensorQuerySet)()

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")

    def __str__(self):
        return f"Sensor {self.sensor_id}"


class SensorLogQuerySet(query.QuerySet):
    pass


class SensorLogManager(models.Manager):
    def current(self) -> query.QuerySet:
        sensor_ids = Sensor.objects.filter(is_active=True).values_list("sensor_id", flat=True)
        return (
            self.get_queryset()
            .filter(sensor_id__in=sensor_ids)
            .order_by("sensor_id", "-created_at")
            .distinct("sensor_id")
        )


class SensorLog(models.Model):
    sensor_id = models.CharField(max_length=32)
    temp = models.DecimalField(max_digits=7, decimal_places=2)
    humidity = models.DecimalField(max_digits=7, decimal_places=2, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SensorLogManager.from_queryset(SensorLogQuerySet)()

    class Meta:
        verbose_name = _("sensor log")
        verbose_name_plural = _("sensor logs")

    def __str__(self):
        return f"Sensor {self.sensor_id} data at {self.created_at}"
