from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Self

from django.conf import settings
from django.contrib import admin
from django.db import models
from django.db.models import query
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


if TYPE_CHECKING:
    from odin.apps.relays.models import Relay


class SensorType(models.TextChoices):
    DS18B20 = "DS18B20", "DS18B20"
    ESP8266 = "ESP8266", "ESP8266"


class SensorQuerySet(query.QuerySet):
    def active(self) -> Self:
        return self.filter(is_active=True)

    def visible(self) -> Self:
        return self.filter(is_visible=True)

    def ds18b20(self) -> Self:
        return self.filter(type=SensorType.DS18B20)

    def esp8266(self) -> Self:
        return self.filter(type=SensorType.ESP8266)


class SensorManager(models.Manager):
    def get_queryset(self) -> SensorQuerySet:
        return SensorQuerySet(self.model, using=self._db)

    def active(self) -> SensorQuerySet:
        return self.get_queryset().active()

    def visible(self) -> SensorQuerySet:
        return self.get_queryset().visible()


class Sensor(models.Model):
    sensor_id = models.CharField(max_length=32, db_index=True, verbose_name=_("Sensor ID"))
    linked_sensor: models.ForeignKey[Sensor] | None = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="linked_sensors",
        verbose_name=_("Linked sensor"),
    )
    relay: models.ForeignKey[Relay] | None = models.ForeignKey(
        "relays.Relay",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sensors",
        verbose_name=_("Relay"),
    )

    name = models.CharField(max_length=32, verbose_name=_("Name"))
    type = models.CharField(max_length=32, choices=SensorType.choices, verbose_name=_("Type"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    is_visible = models.BooleanField(default=True, verbose_name=_("Is visible"))
    order = models.IntegerField(default=0, verbose_name=_("Order"))
    context: models.JSONField[dict] = models.JSONField(default=dict, verbose_name=_("Context"))

    temp: models.DecimalField[Decimal] | None = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    temp_offset: models.DecimalField[Decimal] = models.DecimalField(
        max_digits=7, decimal_places=2, default=Decimal("0.0"), verbose_name=_("Temp offset")
    )
    humidity: models.DecimalField[Decimal] | None = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    humidity_offset: models.DecimalField[Decimal] = models.DecimalField(
        max_digits=7, decimal_places=2, default=Decimal("0.0"), verbose_name=_("Humidity offset")
    )

    created_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    objects = SensorManager()

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")

    def __str__(self):
        return f"Sensor {self.sensor_id}"

    def update(self, temp: Decimal | None, humidity: Decimal | None) -> bool:
        """Store the latest calibrated reading received from the ingest pipeline."""
        updated_fields = []
        if temp is not None:
            self.temp = Decimal(str(temp)) + self.temp_offset
            updated_fields.append("temp")
        if humidity is not None:
            self.humidity = Decimal(str(humidity)) + self.humidity_offset
            updated_fields.append("humidity")
        if not updated_fields:
            return False
        self.save(update_fields=[*updated_fields, "updated_at"])
        return True

    @property
    @admin.display(boolean=True, description=_("Is Alive"))
    def is_alive(self) -> bool:
        return self.updated_at >= timezone.now() - timedelta(minutes=10)

    @property
    def target_temp(self) -> Decimal | None:
        """Fallback value if periods aren't set"""
        if not (value := self.context.get("target_temp")):
            return None
        return Decimal(str(value))

    @property
    def temp_hysteresis(self) -> Decimal | None:
        if not (value := self.context.get("hysteresis")):
            return settings.DEFAULT_TEMP_HYSTERESIS
        return Decimal(str(value))


class SensorLogManager(models.Manager):
    def current(self) -> query.QuerySet:
        return self.get_queryset().filter(sensor__is_active=True).order_by("sensor", "-created_at").distinct("sensor")


class SensorLog(models.Model):
    sensor: models.ForeignKey[Sensor] = models.ForeignKey(
        Sensor, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs", verbose_name=_("Sensor")
    )
    temp: models.DecimalField[Decimal] = models.DecimalField(max_digits=7, decimal_places=2)
    humidity: models.DecimalField[Decimal] = models.DecimalField(max_digits=7, decimal_places=2, null=True)

    synced_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now_add=True)
    created_at: models.DateTimeField[datetime] = models.DateTimeField(null=True, default=None)

    objects = SensorLogManager()

    class Meta:
        verbose_name = _("sensor log")
        verbose_name_plural = _("sensor logs")

    def __str__(self):
        sensor_id = self.sensor.sensor_id if self.sensor else "unknown"
        return f"Sensor {sensor_id} data at {self.synced_at}"
