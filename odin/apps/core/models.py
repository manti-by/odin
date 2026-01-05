from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import query
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class LogQuerySet(models.QuerySet):
    def errors_last_day(self) -> query.QuerySet:
        cutoff = timezone.now() - timedelta(hours=24)
        return self.exclude(levelname__in=("DEBUG", "INFO")).filter(asctime__gte=cutoff).order_by("-asctime")[:10]


class LogManager(models.Manager):
    def get_queryset(self) -> LogQuerySet:
        return LogQuerySet(self.model, using=self._db)

    def errors_last_day(self) -> query.QuerySet:
        return self.get_queryset().errors_last_day()


class Log(models.Model):
    name = models.CharField(max_length=100)
    msg = models.CharField(max_length=100)
    filename = models.CharField(max_length=100)
    levelname = models.CharField(max_length=100)
    asctime = models.DateTimeField()

    objects = LogManager()

    class Meta:
        verbose_name = _("log")
        verbose_name_plural = _("logs")

    def __str__(self):
        return f"Log at {self.asctime}"
