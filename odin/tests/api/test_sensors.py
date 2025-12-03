from django.conf import settings

import pytest
from odin.tests.factories import SensorFactory, SensorDataFactory
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestSensorsView:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:sensors")

    @pytest.mark.parametrize("method", ["put", "patch", "delete"])
    def test_sensors__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_sensors__create(self):
        sensors = list(settings.SENSORS)

        data = SensorDataFactory(sensor_id=sensors[0])
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        
        response = self.client.get(self.url, format="json")
        assert response.data["count"] == 1

        data = SensorDataFactory(sensor_id="test")
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        response = self.client.get(self.url, format="json")
        assert response.data["count"] == 2

    def test_sensors__list(self):
        sensors = list(settings.SENSORS)
        SensorFactory(sensor_id=sensors[0])
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        SensorFactory(sensor_id=sensors[1])
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        SensorFactory(sensor_id=sensors[2])
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

        SensorFactory(sensor_id=sensors[0])
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3