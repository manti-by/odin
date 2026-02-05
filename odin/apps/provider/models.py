from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Traffic(models.Model):
    value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Value"))
    unit = models.CharField(max_length=10, verbose_name=_("Unit"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        verbose_name = _("traffic")
        verbose_name_plural = _("traffic")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.value} {self.unit}"
