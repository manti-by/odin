from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Log(models.Model):
    name = models.CharField(max_length=100)
    msg = models.CharField(max_length=100)
    filename = models.CharField(max_length=100)
    levelname = models.CharField(max_length=100)
    asctime = models.DateTimeField()

    class Meta:
        verbose_name = _("log")
        verbose_name_plural = _("logs")

    def __str__(self):
        return f"Log at {self.asctime}"
