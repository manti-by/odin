from datetime import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _


class BoilerMode(models.TextChoices):
    HEATING = "heating", "Heating"
    MIXED = "mixed", "Mixed"
    OFF = "off", "Off"
    BOILING = "boiling", "Boiling"
    CLEAR_OVERRIDE = "clear_override", "Clear override"


class BoilerLog(models.Model):
    """One snapshot of the boiler's mode and setpoints."""

    hcmode: models.CharField[BoilerMode] = models.CharField(
        max_length=16, choices=BoilerMode.choices, verbose_name=_("Mode")
    )
    flow_temp: models.IntegerField[int] | None = models.IntegerField(
        null=True, blank=True, verbose_name=_("Flow temperature")
    )
    hwc_temp: models.IntegerField[int] | None = models.IntegerField(
        null=True, blank=True, verbose_name=_("Hot-water temperature")
    )

    created_at: models.DateTimeField[datetime] = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name=_("Created at")
    )

    objects = models.Manager()

    class Meta:
        verbose_name = _("boiler log")
        verbose_name_plural = _("boiler logs")
        ordering = ("-created_at",)

    def __str__(self):
        return f"BoilerLog {self.hcmode} @ {self.created_at}"
