import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.tests.factories import SensorFactory, SensorLogDataFactory, SensorLogFactory


@pytest.mark.django_db
class TestSensorsView:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:logs")

    @pytest.mark.parametrize("method", ["put", "patch", "delete"])
    def test_sensors__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_sensors__create(self):
        data = SensorLogDataFactory()
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        response = self.client.get(self.url, format="json")
        assert response.data["count"] == 0

        sensor_01 = SensorFactory()
        data = SensorLogDataFactory(sensor_id=sensor_01.sensor_id)
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        response = self.client.get(self.url, format="json")
        assert response.data["count"] == 1

    def test_sensors__list(self):
        sensor_01 = SensorFactory()

        SensorLogFactory(sensor_id=sensor_01.sensor_id)
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        SensorLogFactory(sensor_id=sensor_01.sensor_id)
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        sensor_02 = SensorFactory()
        SensorLogFactory(sensor_id=sensor_02.sensor_id)
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
