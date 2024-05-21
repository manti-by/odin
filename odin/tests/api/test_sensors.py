from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

import pytest

from odin.tests.factories import SensorFactory


@pytest.mark.django_db
class TestSensorsView:

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:list")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def testt_sensors__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_sensors__list(self):
        SensorFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        SensorFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        SensorFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
