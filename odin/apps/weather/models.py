from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import JSONField, query
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class WeatherProvider(models.TextChoices):
    POGODA_BY = "POGODA_BY", _("Pogoda.by")


class WeatherQuerySet(query.QuerySet):
    pass


class WeatherManager(models.Manager):
    def current(self) -> Weather:
        start_range = timezone.now().replace(minute=0, second=0)
        end_date = start_range + timedelta(minutes=60)
        return self.get_queryset().filter(period__range=(start_range, end_date)).last()


class Weather(models.Model):
    external_id = models.CharField()
    provider = models.CharField(choices=WeatherProvider.choices, default=WeatherProvider.POGODA_BY)
    data = JSONField(default=dict)
    period = models.DateTimeField(db_index=True)
    synced_at = models.DateTimeField(db_index=True, auto_now=True)

    objects = WeatherManager.from_queryset(WeatherQuerySet)()

    class Meta:
        verbose_name = _("weather")
        verbose_name_plural = _("weather")

    def __str__(self):
        return f"Weather for {self.period}"
