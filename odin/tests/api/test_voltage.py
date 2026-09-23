from decimal import Decimal

import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.tests.factories import VoltageLogFactory


@pytest.mark.django_db
class TestVoltageCurrentAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:electricity:voltage")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_voltage__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_voltage__returns_null_when_no_data(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data is None

    def test_voltage__returns_latest_value(self):
        VoltageLogFactory(voltage=Decimal("230.50"))

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["voltage"] == "230.50"
        assert "created_at" in response.data
