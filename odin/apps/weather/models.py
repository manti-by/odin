from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _


class WeatherProvider(models.TextChoices):
    POGODA_BY = "POGODA_BY", _("Pogoda.by")


class Weather(models.Model):
    external_id = models.CharField()
    provider = models.CharField(choices=WeatherProvider.choices, default=WeatherProvider.POGODA_BY)
    data = JSONField(default=dict)
    period = models.DateTimeField(db_index=True)
    synced_at = models.DateTimeField(db_index=True, auto_now=True)

    class Meta:
        verbose_name = _("weather")
        verbose_name_plural = _("weather")

    def __str__(self):
        return f"Weather for {self.period}"
