from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import JSONField, query
from django.db.utils import cached_property
from django.utils import formats, timezone
from django.utils.translation import gettext_lazy as _


class WeatherProvider(models.TextChoices):
    POGODA_BY = "POGODA_BY", "Pogoda.by"


class WeatherManager(models.Manager):
    def current(self) -> Weather:
        start_range = timezone.now().replace(minute=0, second=0)
        end_date = start_range + timedelta(minutes=60)

        queryset = self.get_queryset().filter(period__range=(start_range, end_date)).order_by("-period")
        return queryset.last() or self.get_queryset().last()


class Weather(models.Model):
    external_id = models.CharField()
    provider = models.CharField(choices=WeatherProvider.choices, default=WeatherProvider.POGODA_BY)
    data: models.JSONField[dict] = JSONField(default=dict)
    period: models.DateTimeField[datetime] = models.DateTimeField(db_index=True)
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
        return any([v for x, v in self.attrs.items() if x != "attr"])

    @staticmethod
    def temp_display_localized(temp: Decimal | None) -> str:
        if temp is None:
            return "--"
        temp_display = formats.localize(round(temp, 1), use_l10n=False)
        return f"+{temp_display}" if temp > 0 else f"{temp_display}"

    @property
    def temp(self) -> Decimal | None:
        if (temp := self.data.get("temp", {}).get("avg")) is not None:
            return Decimal(temp)
        return None

    @property
    def temp_display(self) -> str:
        return self.temp_display_localized(self.temp)

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
        return self.temp_display_localized(self.temp_min)

    @cached_property
    def temp_max(self) -> Decimal | None:
        if weather := self.current_weather_set.last():
            return weather.temp
        return None

    @property
    def temp_max_display(self) -> str:
        return self.temp_display_localized(self.temp_max)

    @property
    def pressure(self) -> int | None:
        if pressure := self.data.get("pressure"):
            return int(pressure * 100 / 133.32)
        return None
