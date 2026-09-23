from datetime import date, timedelta
from decimal import Decimal

import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.currency.models import Currency
from odin.tests.factories import ExchangeRateFactory


@pytest.mark.django_db
class TestExchangeRateCurrentAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:currency:rates")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_currency__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_currency__empty(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"rates": [], "trends": {}}

    def test_currency__rates_and_trends(self):
        today = date.today()
        yesterday = today - timedelta(days=1)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)
        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=yesterday)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        assert len(response.data["rates"]) == 1
        assert response.data["rates"][0]["currency"] == Currency.USD
        assert response.data["rates"][0]["rate_per_unit"] == "3.2500"
        assert response.data["trends"]["USD"] is not None
