from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from odin.apps.currency.models import Currency
from odin.tests.factories import ExchangeRateFactory, SensorFactory, VoltageLogFactory, WeatherFactory


@pytest.mark.django_db
@pytest.mark.views
class TestIndexView:
    @patch("odin.apps.core.services.subprocess.run")
    def test_index(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"

        response = client.get(reverse("index"), follow=True)
        assert response.status_code == status.HTTP_200_OK

    @patch("odin.apps.core.services.subprocess.run")
    def test_index_uses_cached_context(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"

        SensorFactory(is_active=True)
        VoltageLogFactory()
        WeatherFactory()

        with patch.object(cache, "get") as mock_get:
            mock_get.return_value = {
                "weather": None,
                "sensors": [],
                "home_sensors_is_alive": True,
                "boiler_sensors_is_alive": True,
                "error_logs": [],
                "voltage": None,
                "voltage_chart": "",
                "voltage_values": [],
            }
            response = client.get(reverse("index"), follow=True)
            assert response.status_code == 200

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
