from __future__ import annotations

from django.db import models
from django.db.models import query
from django.utils.translation import gettext_lazy as _


class VoltageLogQuerySet(query.QuerySet):
    pass


class VoltageLogManager(models.Manager):
    def get_queryset(self) -> VoltageLogQuerySet:
        return VoltageLogQuerySet(self.model, using=self._db)


class VoltageLog(models.Model):
    voltage = models.DecimalField(max_digits=7, decimal_places=2, verbose_name=_("Voltage"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"), db_index=True)

    objects = VoltageLogManager()

    class Meta:
        verbose_name = _("voltage log")
        verbose_name_plural = _("voltage logs")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Voltage {self.voltage}V at {self.created_at}"
