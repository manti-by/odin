from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models import JSONField, query
from django.db.utils import cached_property
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class WeatherProvider(models.TextChoices):
    POGODA_BY = "POGODA_BY", "Pogoda.by"


class WeatherManager(models.Manager):
    def current(self) -> Weather:
        start_range = timezone.now().replace(minute=0, second=0)
        end_date = start_range + timedelta(minutes=60)

        queryset = self.get_queryset().filter(period__range=(start_range, end_date)).order_by("-period")
        return queryset.last() if queryset.exists() else self.get_queryset().last()


class Weather(models.Model):
    external_id = models.CharField()
    provider = models.CharField(choices=WeatherProvider.choices, default=WeatherProvider.POGODA_BY)
    data = JSONField(default=dict)
    period = models.DateTimeField(db_index=True)
    synced_at = models.DateTimeField(db_index=True, auto_now=True)

    objects = WeatherManager()

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
    def temp(self) -> Decimal | None:
        if (temp := self.data.get("temp", {}).get("avg")) is not None:
            return Decimal(temp)
        return None

    @property
    def temp_display(self) -> str:
        if self.temp is None:
            return "--"
        return f"+{round(self.temp, 1)}" if self.temp > 0 else f"{round(self.temp, 1)}"

    @cached_property
    def current_weather_set(self) -> query.QuerySet[Weather]:
        start_range, end_date = self.period - timedelta(hours=12), self.period + timedelta(hours=12)
        return Weather.objects.filter(period__range=(start_range, end_date)).order_by("data__temp")

    @cached_property
    def temp_min(self) -> Decimal | None:
        if weather := self.current_weather_set.first():
            return weather.temp
        return None

    @property
    def temp_min_display(self) -> str:
        if self.temp_min is None:
            return "--"
        return f"+{round(self.temp_min, 1)}" if self.temp_min > 0 else f"{round(self.temp_min, 1)}"

    @cached_property
    def temp_max(self) -> Decimal | None:
        if weather := self.current_weather_set.last():
            return weather.temp
        return None

    @property
    def temp_max_display(self) -> str:
        if self.temp_max is None:
            return "--"
        return f"+{round(self.temp_max, 1)}" if self.temp_max > 0 else f"{round(self.temp_max, 1)}"

    @property
    def pressure(self) -> int | None:
        if pressure := self.data.get("pressure"):
            return int(pressure * 100 / 133.32)
        return None
