from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from odin.apps.currency.models import Currency, ExchangeRate


def get_exchange_rate_trends() -> dict[str, Decimal | None]:
    today_rates = ExchangeRate.objects.current()
    if not today_rates:
        return {}

    today_date = today_rates[0].date
    yesterday = today_date - timedelta(days=1)

    yesterday_rates = {r.currency: r for r in ExchangeRate.objects.filter(date=yesterday)}

    if not yesterday_rates:
        prior_date = (
            ExchangeRate.objects.filter(date__lt=today_date).order_by("-date").values_list("date", flat=True).first()
        )
        if prior_date:
            yesterday_rates = {r.currency: r for r in ExchangeRate.objects.filter(date=prior_date)}

    trends: dict[str, Decimal | None] = {}
    today_rates_by_currency = {r.currency: r for r in today_rates}

    for currency in Currency.values:
        today_rate = today_rates_by_currency.get(currency)
        prior_rate = yesterday_rates.get(currency)

        if today_rate and prior_rate:
            trends[currency] = today_rate.rate_per_unit - prior_rate.rate_per_unit
        else:
            trends[currency] = None

    return trends
