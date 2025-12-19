from __future__ import annotations

from django.db import models
from django.db.models import query
from django.utils.translation import gettext_lazy as _


class RelayType(models.TextChoices):
    PUMP = "PUMP", _("Pump")
    SERVO = "SERVO", _("Servo")
    VALVE = "VALVE", _("Valve")


class RelayQuerySet(query.QuerySet):
    def active(self) -> query.QuerySet:
        return self.filter(is_active=True)


class RelayManager(models.Manager):
    def get_queryset(self) -> RelayQuerySet:
        return RelayQuerySet(self.model, using=self._db)

    def active(self) -> query.QuerySet:
        return self.get_queryset().active()


class Relay(models.Model):
    relay_id = models.CharField(max_length=32, verbose_name=_("Relay ID"))
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
        return self.context.get("state", "UNKNOWN")
