from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import query
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


class SensorType(models.TextChoices):
    DS18B20 = "DS18B20", "DS18B20"
    ESP8266 = "ESP8266", "ESP8266"


class SensorQuerySet(query.QuerySet):
    def active(self) -> query.QuerySet:
        return self.filter(is_active=True)

    def ds18b20(self) -> query.QuerySet:
        return self.filter(type=SensorType.DS18B20)

    def esp8266(self) -> query.QuerySet:
        return self.filter(type=SensorType.ESP8266)


class SensorManager(models.Manager):
    def get_queryset(self) -> SensorQuerySet:
        return SensorQuerySet(self.model, using=self._db)

    def active(self) -> query.QuerySet:
        return self.get_queryset().active()


class Sensor(models.Model):
    sensor_id = models.CharField(max_length=32)
    name = models.CharField(max_length=32)
    type = models.CharField(max_length=32, choices=SensorType.choices)
    is_active = models.BooleanField(default=True)
    context = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SensorManager()

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")

    def __str__(self):
        return f"Sensor {self.sensor_id}"

    @cached_property
    def latest_log(self) -> SensorLog:
        return SensorLog.objects.filter(sensor_id=self.sensor_id).order_by("-created_at").last()

    @property
    def temp(self) -> Decimal | None:
        if self.latest_log:
            return self.latest_log.temp
        return None


class SensorLogManager(models.Manager):
    def current(self) -> query.QuerySet:
        sensor_ids = Sensor.objects.active().values_list("sensor_id", flat=True)
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

    synced_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(null=True, default=None)

    objects = SensorLogManager()

    class Meta:
        verbose_name = _("sensor log")
        verbose_name_plural = _("sensor logs")

    def __str__(self):
        return f"Sensor {self.sensor_id} data at {self.synced_at}"
