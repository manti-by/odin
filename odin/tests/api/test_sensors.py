import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.sensors.models import Sensor, SensorType
from odin.tests.factories import SensorFactory


@pytest.mark.django_db
class TestSensorsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:list")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_sensors__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_sensors__list(self):
        sensor = SensorFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        for field in ("sensor_id", "name", "type"):
            assert field in response.data["results"][0]
            assert getattr(sensor, field) == response.data["results"][0][field]

        SensorFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_sensors__update(self):
        sensor: Sensor = SensorFactory()  # noqa
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))
        response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor.refresh_from_db()
        assert sensor.context["target_temp"] == "25.5"

    def test_sensors__list_empty(self):
        """Test that list returns empty result when no sensors exist."""
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert response.data["results"] == []

    def test_sensors__list_only_active(self):
        """Test that list returns only active sensors."""
        active_sensor = SensorFactory(is_active=True)
        SensorFactory(is_active=False)
        SensorFactory(is_active=False)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["sensor_id"] == active_sensor.sensor_id

    def test_sensors__list_different_types(self):
        """Test that list returns sensors of all types."""
        ds18b20_sensor = SensorFactory(type=SensorType.DS18B20)
        esp8266_sensor = SensorFactory(type=SensorType.ESP8266)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        sensor_ids = [s["sensor_id"] for s in response.data["results"]]
        assert ds18b20_sensor.sensor_id in sensor_ids
        assert esp8266_sensor.sensor_id in sensor_ids

    def test_sensors__update_with_existing_context(self):
        """Test that update merges with existing context."""
        sensor = SensorFactory(context={"existing_key": "existing_value", "target_temp": "20.0"})
        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))

        response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor.refresh_from_db()
        assert sensor.context["target_temp"] == "25.5"
        assert sensor.context["existing_key"] == "existing_value"

    def test_sensors__update_non_existent_sensor(self):
        """Test that update returns 404 for non-existent sensor."""
        url = reverse("api:v1:sensors:update", args=("non_existent_id",))
        response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_sensors__update_with_empty_context(self):
        """Test that update with empty context dict works."""
        sensor = SensorFactory(context={"existing_key": "existing_value"})
        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))

        response = self.client.patch(url, data={"context": {}}, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor.refresh_from_db()
        # Empty context should preserve existing context (update, not replace)
        assert "existing_key" in sensor.context

    def test_sensors__response_fields(self):
        """Test that response includes all expected fields."""
        SensorFactory(sensor_id="test_sensor", name="Test Sensor", type=SensorType.DS18B20)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor_data = response.data["results"][0]
        expected_fields = {"sensor_id", "name", "type", "context", "created_at"}
        assert expected_fields.issubset(set(sensor_data.keys()))
        assert sensor_data["sensor_id"] == "test_sensor"
        assert sensor_data["name"] == "Test Sensor"
        assert sensor_data["type"] == SensorType.DS18B20
