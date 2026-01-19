from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class CurrencyExchangeRateManager(models.Manager):
    def current(self) -> list[ExchangeRate]:
        latest_date = self.get_queryset().order_by("-date").values_list("date", flat=True).first()
        if not latest_date:
            return []
        return list(self.get_queryset().filter(date=latest_date))


class Currency(models.TextChoices):
    USD = "USD", _("US Dollar")
    EUR = "EUR", _("Euro")
    RUB = "RUB", _("Russian Ruble")


class ExchangeRate(models.Model):
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        db_index=True,
    )
    rate: models.DecimalField[Decimal] = models.DecimalField(max_digits=10, decimal_places=4)
    scale: models.PositiveIntegerField[int] = models.PositiveIntegerField(default=1)
    date = models.DateField(db_index=True)
    data = models.JSONField(default=dict)
    synced_at = models.DateTimeField(auto_now=True)

    objects = CurrencyExchangeRateManager()

    class Meta:
        verbose_name = _("exchange rate")
        verbose_name_plural = _("exchange rates")
        unique_together = ["currency", "date"]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.currency} - {self.rate} BYN ({self.date})"

    @property
    def rate_per_unit(self) -> Decimal:
        return self.rate / self.scale
