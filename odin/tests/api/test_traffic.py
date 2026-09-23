from decimal import Decimal

import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestTrafficCurrentAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:provider:traffic")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_traffic__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_traffic__returns_null_when_no_data(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data is None

    def test_traffic__returns_latest_value(self):
        Traffic.objects.create(value=Decimal("123.45"), unit="GB")

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["value"] == "123.45"
        assert response.data["unit"] == "GB"
