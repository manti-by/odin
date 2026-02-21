from datetime import date, timedelta
from decimal import Decimal

import pytest

from odin.apps.currency.models import Currency
from odin.apps.currency.services import get_exchange_rate_trends
from odin.tests.factories import ExchangeRateFactory


@pytest.mark.django_db
class TestExchangeRateTrends:
    def test_trends_returns_correct_diffs_when_yesterday_data_exists(self):
        today = date.today()
        yesterday = today - timedelta(days=1)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)
        ExchangeRateFactory(currency=Currency.EUR, rate=Decimal("3.5000"), date=today)
        ExchangeRateFactory(currency=Currency.RUB, rate=Decimal("3.7500"), date=today, scale=100)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=yesterday)
        ExchangeRateFactory(currency=Currency.EUR, rate=Decimal("3.6000"), date=yesterday)
        ExchangeRateFactory(currency=Currency.RUB, rate=Decimal("3.6500"), date=yesterday, scale=100)

        trends = get_exchange_rate_trends()

        assert trends[Currency.USD] == Decimal("0.1000")
        assert trends[Currency.EUR] == Decimal("-0.1000")
        assert trends[Currency.RUB] == Decimal("0.0010")

    def test_trends_uses_earlier_date_when_yesterday_missing(self):
        today = date.today()
        two_days_ago = today - timedelta(days=2)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)
        ExchangeRateFactory(currency=Currency.EUR, rate=Decimal("3.5000"), date=today)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=two_days_ago)
        ExchangeRateFactory(currency=Currency.EUR, rate=Decimal("3.6000"), date=two_days_ago)

        trends = get_exchange_rate_trends()

        assert trends[Currency.USD] == Decimal("0.1000")
        assert trends[Currency.EUR] == Decimal("-0.1000")

    def test_trends_returns_none_for_currency_without_prior_data(self):
        today = date.today()

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)

        trends = get_exchange_rate_trends()

        assert trends[Currency.USD] is None
        assert trends[Currency.EUR] is None
        assert trends[Currency.RUB] is None

    def test_trends_returns_empty_dict_when_no_current_rates(self):
        trends = get_exchange_rate_trends()

        assert trends == {}
