from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.db.models import query
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


if TYPE_CHECKING:
    from odin.apps.relays.models import Relay


class SensorType(models.TextChoices):
    DS18B20 = "DS18B20", "DS18B20"
    ESP8266 = "ESP8266", "ESP8266"


class SensorQuerySet(query.QuerySet):
    def active(self) -> query.QuerySet:
        return self.filter(is_active=True)

    def visible(self) -> query.QuerySet:
        return self.filter(is_visible=True)

    def ds18b20(self) -> query.QuerySet:
        return self.filter(type=SensorType.DS18B20)

    def esp8266(self) -> query.QuerySet:
        return self.filter(type=SensorType.ESP8266)


class SensorManager(models.Manager):
    def get_queryset(self) -> SensorQuerySet:
        return SensorQuerySet(self.model, using=self._db)

    def active(self) -> query.QuerySet:
        return self.get_queryset().active()

    def visible(self) -> query.QuerySet:
        return self.get_queryset().visible()


class Sensor(models.Model):
    sensor_id = models.CharField(max_length=32, db_index=True, verbose_name=_("Sensor ID"))
    linked_sensor_id = models.CharField(
        max_length=32, db_index=True, null=True, blank=True, verbose_name=_("Linked sensor ID")
    )
    relay_id = models.CharField(max_length=32, db_index=True, null=True, blank=True, verbose_name=_("Relay ID"))

    name = models.CharField(max_length=32, verbose_name=_("Name"))
    type = models.CharField(max_length=32, choices=SensorType.choices, verbose_name=_("Type"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    is_visible = models.BooleanField(default=True, verbose_name=_("Is visible"))
    order = models.IntegerField(default=0, verbose_name=_("Order"))
    context = models.JSONField(default=dict, verbose_name=_("Context"))

    temp_offset = models.DecimalField(
        max_digits=7, decimal_places=2, default=Decimal("0.0"), verbose_name=_("Temp offset")
    )
    humidity_offset = models.DecimalField(
        max_digits=7, decimal_places=2, default=Decimal("0.0"), verbose_name=_("Humidity offset")
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    objects = SensorManager()

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")

    def __str__(self):
        return f"Sensor {self.sensor_id}"

    @cached_property
    def latest_log(self) -> SensorLog:
        return SensorLog.objects.filter(sensor_id=self.sensor_id).order_by("created_at").last()

    @cached_property
    def linked_sensor(self) -> Sensor | None:
        if not self.linked_sensor_id:
            return None

        return Sensor.objects.filter(sensor_id=self.linked_sensor_id).order_by("created_at").last()

    @cached_property
    def relay(self) -> Relay | None:
        from odin.apps.relays.models import Relay

        if not self.relay_id:
            return None

        return Relay.objects.filter(relay_id=self.relay_id).order_by("created_at").last()

    @property
    def temp(self) -> Decimal | None:
        if self.latest_log:
            return self.latest_log.temp + self.temp_offset
        return None

    @property
    def target_temp(self) -> Decimal | None:
        if not (value := self.context.get("target_temp")):
            return None
        return Decimal(str(value))

    @property
    def temp_hysteresis(self) -> Decimal | None:
        if not (value := self.context.get("hysteresis")):
            return settings.DEFAULT_TEMP_HYSTERESIS
        return Decimal(str(value))

    @property
    def humidity(self) -> Decimal | None:
        if self.latest_log:
            return self.latest_log.humidity + self.humidity_offset
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
