from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models import JSONField, query
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class WeatherProvider(models.TextChoices):
    POGODA_BY = "POGODA_BY", _("Pogoda.by")


class WeatherQuerySet(query.QuerySet):
    def current_day(self) -> Weather:
        start_range = timezone.now().replace(minute=0, second=0)
        end_date = start_range + timedelta(minutes=60)
        return self.filter(period__range=(start_range, end_date))


class WeatherManager(models.Manager):
    def current(self) -> Weather:
        return self.get_queryset().current_day().last()


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

    @property
    def attrs(self) -> dict:
        return self.data.get("attributes", {})

    @property
    def has_attrs(self) -> bool:
        return any(self.attrs.values())

    @property
    def temp(self) -> Decimal:
        if temp := self.data.get("temp", {}).get("avg"):
            return Decimal(temp)
        return Decimal(0)

    @property
    def temp_display(self) -> str:
        return f"+{round(self.temp, 1)}" if self.temp > 0 else f"{round(self.temp, 1)}"

    @property
    def temp_min(self) -> Decimal:
        if temp := self.data.get("temp", {}).get("min"):
            return Decimal(temp)
        return Decimal(0)

    @property
    def temp_min_display(self) -> str:
        return f"+{round(self.temp_min, 1)}" if self.temp_min > 0 else f"{round(self.temp_min, 1)}"

    @property
    def temp_max(self) -> Decimal:
        if temp := self.data.get("temp", {}).get("max"):
            return Decimal(temp)
        return Decimal(0)

    @property
    def temp_max_display(self) -> str:
        return f"+{round(self.temp_max, 1)}" if self.temp_max > 0 else f"{round(self.temp_max, 1)}"

    @property
    def pressure(self) -> int | None:
        if pressure := self.data.get("pressure"):
            return int(pressure * 100 / 133.32)
        return None
