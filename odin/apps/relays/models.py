from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models import query
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


if TYPE_CHECKING:
    from odin.apps.sensors.models import Sensor


class RelayType(models.TextChoices):
    PUMP = "PUMP", _("Pump")
    SERVO = "SERVO", _("Servo")
    VALVE = "VALVE", _("Valve")


class RelayState(models.TextChoices):
    ON = "ON", _("ON")
    OFF = "OFF", _("OFF")
    UNKNOWN = "UNKNOWN", _("UNKNOWN")


class RelayQuerySet(query.QuerySet):
    def active(self) -> query.QuerySet:
        return self.filter(is_active=True)


class RelayManager(models.Manager):
    def get_queryset(self) -> RelayQuerySet:
        return RelayQuerySet(self.model, using=self._db)

    def active(self) -> query.QuerySet:
        return self.get_queryset().active()


class Relay(models.Model):
    relay_id = models.CharField(max_length=32, db_index=True, verbose_name=_("Relay ID"))
    name = models.CharField(max_length=32, verbose_name=_("Name"))
    type = models.CharField(max_length=32, choices=RelayType.choices, verbose_name=_("Type"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    context = models.JSONField(default=dict, verbose_name=_("Context"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    objects = RelayManager()

    class Meta:
        verbose_name = _("relay")
        verbose_name_plural = _("relays")

    def __str__(self):
        return f"Relay {self.relay_id}"

    @property
    def state(self) -> str:
        return self.context.get("state", RelayState.UNKNOWN)

    @cached_property
    def sensor(self) -> Sensor | None:
        from odin.apps.sensors.models import Sensor

        return Sensor.objects.filter(relay_id=self.relay_id).order_by("created_at").last()

    @property
    def pump_target_state(self) -> RelayState.choices:
        now = timezone.localtime()
        day, hour = now.strftime("%w"), now.strftime("%H")

        state = self.context.get("schedule", {}).get(day, {}).get(hour)
        if state is not None:
            return RelayState.ON if state else RelayState.OFF
        return RelayState.UNKNOWN

    @property
    def servo_target_state(self) -> RelayState.choices:
        if not self.sensor or self.sensor.temp is None:
            return RelayState.UNKNOWN

        target_temp_min = self.sensor.target_temp - self.sensor.temp_hysteresis
        target_temp_max = self.sensor.target_temp + self.sensor.temp_hysteresis

        if target_temp_min < self.sensor.temp < target_temp_max:
            return RelayState.OFF
        return RelayState.ON

    @property
    def target_state(self) -> RelayState.choices:
        match self.type:
            case RelayType.PUMP:
                return self.pump_target_state
            case RelayType.SERVO:
                return self.servo_target_state
            case _:
                return RelayState.UNKNOWN
