from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from odin.apps.currency.models import Currency
from odin.tests.factories import ExchangeRateFactory


@pytest.mark.django_db
@pytest.mark.views
class TestIndexView:
    def test_index_returns_spa_error_when_build_missing(self, client):
        response = client.get(reverse("index"), follow=True)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    @patch("odin.apps.core.services.subprocess.run")
    def test_index_exchange_rates_trends_up_arrow(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"
        cache.clear()

        today = date.today()
        yesterday = today - timedelta(days=1)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)
        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=yesterday)

        from odin.apps.core.services import build_index_context

        context = build_index_context()
        assert context["exchange_rates_trends"]["USD"] > 0

    @patch("odin.apps.core.services.subprocess.run")
    def test_index_exchange_rates_trends_down_arrow(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"
        cache.clear()

        today = date.today()
        yesterday = today - timedelta(days=1)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=today)
        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=yesterday)

        from odin.apps.core.services import build_index_context

        context = build_index_context()
        assert context["exchange_rates_trends"]["USD"] < 0

    @patch("odin.apps.core.services.subprocess.run")
    def test_index_exchange_rates_no_arrow_when_no_prior_data(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"
        cache.clear()

        today = date.today()

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)

        from odin.apps.core.services import build_index_context

        context = build_index_context()
        assert context["exchange_rates_trends"]["USD"] is None
