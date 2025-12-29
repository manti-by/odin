from datetime import timedelta

import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.sensors.models import SensorType
from odin.tests.factories import SensorFactory, SensorLogDataFactory, SensorLogFactory


@pytest.mark.django_db
class TestSensorsLogsAPI:
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

        sensor_02 = SensorFactory()
        data = SensorLogDataFactory(sensor_id=sensor_02.sensor_id, created_at=None)
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        response = self.client.get(self.url, format="json")
        assert response.data["count"] == 2
        assert response.data["results"][-1]["created_at"]

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

    def test_sensors__create_with_humidity(self):
        """Test that log creation works with humidity field."""
        sensor = SensorFactory()
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id, humidity=65.5)

        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["humidity"] == "65.50"

    def test_sensors__create_without_humidity(self):
        """Test that humidity is optional when creating logs."""
        sensor = SensorFactory()
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id)
        # Remove humidity from data
        del data["humidity"]

        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "humidity" not in response.data or response.data["humidity"] is None

    def test_sensors__create_missing_required_fields(self):
        """Test that creation fails with missing required fields."""
        # Missing sensor_id
        data = {"temp": "22.5"}
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Missing temp
        data = {"sensor_id": "test_sensor"}
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sensors__create_invalid_temp(self):
        """Test that creation fails with invalid temperature value."""
        sensor = SensorFactory()
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id, temp="invalid")

        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sensors__create_invalid_humidity(self):
        """Test that creation fails with invalid humidity value."""
        sensor = SensorFactory()
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id, humidity="invalid")

        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sensors__create_auto_assigns_created_at(self):
        """Test that created_at is auto-assigned when not provided."""
        sensor = SensorFactory()
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id, created_at=None)

        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["created_at"] is not None

    def test_sensors__list_only_current_logs(self):
        """Test that list returns only current (latest) log per active sensor."""
        sensor1 = SensorFactory(is_active=True, sensor_id="sensor1")
        sensor2 = SensorFactory(is_active=True, sensor_id="sensor2")
        inactive_sensor = SensorFactory(is_active=False, sensor_id="inactive")

        # Create multiple logs for sensor1 - only latest should appear
        SensorLogFactory(sensor_id=sensor1.sensor_id, created_at=timezone.now() - timedelta(hours=2))
        SensorLogFactory(sensor_id=sensor1.sensor_id, created_at=timezone.now() - timedelta(hours=1))
        latest_log = SensorLogFactory(sensor_id=sensor1.sensor_id, created_at=timezone.now())

        # Create log for sensor2
        SensorLogFactory(sensor_id=sensor2.sensor_id, created_at=timezone.now())

        # Create log for inactive sensor - should not appear
        SensorLogFactory(sensor_id=inactive_sensor.sensor_id, created_at=timezone.now())

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        sensor_ids = [log["sensor_id"] for log in response.data["results"]]
        assert sensor1.sensor_id in sensor_ids
        assert sensor2.sensor_id in sensor_ids
        assert inactive_sensor.sensor_id not in sensor_ids

        # Verify latest log for sensor1 is returned
        sensor1_log = next(log for log in response.data["results"] if log["sensor_id"] == sensor1.sensor_id)
        assert sensor1_log["sensor_id"] == latest_log.sensor_id

    def test_sensors__list_different_sensor_types(self):
        """Test that list works with different sensor types."""
        ds18b20_sensor = SensorFactory(type=SensorType.DS18B20, is_active=True)
        esp8266_sensor = SensorFactory(type=SensorType.ESP8266, is_active=True)

        SensorLogFactory(sensor_id=ds18b20_sensor.sensor_id)
        SensorLogFactory(sensor_id=esp8266_sensor.sensor_id)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        sensor_ids = [log["sensor_id"] for log in response.data["results"]]
        assert ds18b20_sensor.sensor_id in sensor_ids
        assert esp8266_sensor.sensor_id in sensor_ids

    def test_sensors__list_empty(self):
        """Test that list returns empty when no active sensors with logs exist."""
        # Create inactive sensor with log
        inactive_sensor = SensorFactory(is_active=False)
        SensorLogFactory(sensor_id=inactive_sensor.sensor_id)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_sensors__response_fields(self):
        """Test that response includes all expected fields."""
        sensor = SensorFactory(is_active=True)
        log = SensorLogFactory(sensor_id=sensor.sensor_id, temp=22.5, humidity=65.0)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        log_data = response.data["results"][0]
        assert log_data["sensor_id"] == log.sensor_id
        assert float(log_data["temp"]) == float(log.temp)

    def test_sensors__create_updates_existing_context(self):
        """Test that creating a log for a sensor that already has a log updates the current log."""
        sensor = SensorFactory(is_active=True)
        SensorLogFactory(sensor_id=sensor.sensor_id, temp=20.0, created_at=timezone.now() - timedelta(hours=1))

        # Create new log for same sensor
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id, temp=22.5)

        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # A list should now show the new log (latest)
        list_response = self.client.get(self.url, format="json")
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.data["count"] == 1
        assert list_response.data["results"][0]["sensor_id"] == sensor.sensor_id

    def test_sensors__create_with_extreme_temperatures(self):
        """Test that creation works with extreme temperature values."""
        sensor = SensorFactory()
        # Very low temperature
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id, temp=-40.0)
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # Very high temperature
        data = SensorLogDataFactory(sensor_id=sensor.sensor_id, temp=50.0)
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
