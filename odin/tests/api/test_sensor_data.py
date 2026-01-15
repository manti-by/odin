from datetime import timedelta

import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.sensors.models import SensorType
from odin.tests.factories import SensorFactory, SensorLogFactory


@pytest.mark.django_db
class TestDS18B20DataAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:ds18b20")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_ds18b20__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_ds18b20__empty_response_no_sensors(self):
        """Test that API returns empty response when no DS18B20 sensors exist."""
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"timestamps": [], "sensors": []}

    def test_ds18b20__empty_response_no_logs(self):
        """Test that API returns empty response when no logs exist for DS18B20 sensors."""
        sensor = SensorFactory(type=SensorType.DS18B20, is_active=True)
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "timestamps": [],
            "sensors": [{"data": [], "name": sensor.name, "sensor_id": sensor.sensor_id}],
        }

    def test_ds18b20__only_ds18b20_sensors(self):
        """Test that only DS18B20 sensors are included, not ESP8266."""
        # Create DS18B20 sensor with logs
        ds18b20_sensor = SensorFactory(type=SensorType.DS18B20, is_active=True, sensor_id="ds18b20_1")
        now = timezone.now()
        SensorLogFactory(sensor_id=ds18b20_sensor.sensor_id, created_at=now)

        # Create ESP8266 sensor with logs - should not be included
        esp8266_sensor = SensorFactory(type=SensorType.ESP8266, is_active=True, sensor_id="esp8266_1")
        SensorLogFactory(sensor_id=esp8266_sensor.sensor_id, created_at=now)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 1
        assert response.data["sensors"][0]["sensor_id"] == "ds18b20_1"

    def test_ds18b20__only_active_sensors(self):
        """Test that only active sensors are included."""
        active_sensor = SensorFactory(type=SensorType.DS18B20, is_active=True, sensor_id="active_1")
        inactive_sensor = SensorFactory(type=SensorType.DS18B20, is_active=False, sensor_id="inactive_1")
        now = timezone.now()
        SensorLogFactory(sensor_id=active_sensor.sensor_id, created_at=now)
        SensorLogFactory(sensor_id=inactive_sensor.sensor_id, created_at=now)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 1
        assert response.data["sensors"][0]["sensor_id"] == "active_1"

    def test_ds18b20__only_last_12_hours(self):
        """Test that only logs from the last 12 hours are included."""
        sensor = SensorFactory(type=SensorType.DS18B20, is_active=True, sensor_id="sensor_1")
        now = timezone.now()

        # Create log within last 12 hours
        recent_log_time = now - timedelta(hours=6)
        SensorLogFactory(sensor_id=sensor.sensor_id, created_at=recent_log_time, temp=22.5)

        # Create log older than 12 hours - should not be included
        old_log_time = now - timedelta(hours=13)
        SensorLogFactory(sensor_id=sensor.sensor_id, created_at=old_log_time, temp=21.0)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 1
        assert len(response.data["timestamps"]) > 0
        # Verify the recent temperature is in the data
        sensor_data = response.data["sensors"][0]
        assert 22.5 in sensor_data["data"]

    def test_ds18b20__data_structure(self):
        """Test that the response has the correct data structure."""
        sensor = SensorFactory(type=SensorType.DS18B20, is_active=True, sensor_id="sensor_1", name="Test Sensor")
        now = timezone.now()
        SensorLogFactory(sensor_id=sensor.sensor_id, created_at=now, temp=22.5)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        # Check top-level structure
        assert "timestamps" in response.data
        assert "sensors" in response.data
        assert isinstance(response.data["timestamps"], list)
        assert isinstance(response.data["sensors"], list)

        if response.data["sensors"]:
            sensor_data = response.data["sensors"][0]
            # Check sensor structure
            assert "sensor_id" in sensor_data
            assert "name" in sensor_data
            assert "data" in sensor_data
            assert sensor_data["sensor_id"] == "sensor_1"
            assert sensor_data["name"] == "Test Sensor"
            assert isinstance(sensor_data["data"], list)
            # Timestamps and data should have the same length
            assert len(response.data["timestamps"]) == len(sensor_data["data"])

    def test_ds18b20__multiple_sensors_and_logs(self):
        """Test with multiple sensors and multiple logs."""
        sensor1 = SensorFactory(type=SensorType.DS18B20, is_active=True, sensor_id="sensor_1", name="Sensor 1")
        sensor2 = SensorFactory(type=SensorType.DS18B20, is_active=True, sensor_id="sensor_2", name="Sensor 2")

        now = timezone.now()
        # Create multiple logs for sensor1
        SensorLogFactory(sensor_id=sensor1.sensor_id, created_at=now - timedelta(hours=2), temp=22.0)
        SensorLogFactory(sensor_id=sensor1.sensor_id, created_at=now - timedelta(hours=1), temp=22.5)

        # Create log for sensor2
        SensorLogFactory(sensor_id=sensor2.sensor_id, created_at=now - timedelta(hours=1), temp=23.0)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 2

        # Verify both sensors are present
        sensor_ids = [s["sensor_id"] for s in response.data["sensors"]]
        assert "sensor_1" in sensor_ids
        assert "sensor_2" in sensor_ids


@pytest.mark.django_db
class TestESP8266DataAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:esp8266")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_esp8266__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_esp8266__empty_response_no_sensors(self):
        """Test that API returns empty response when no ESP8266 sensors exist."""
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"timestamps": [], "sensors": []}

    def test_esp8266__empty_response_no_logs(self):
        """Test that API returns empty response when no logs exist for ESP8266 sensors."""
        sensor = SensorFactory(type=SensorType.ESP8266, is_active=True)
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "timestamps": [],
            "sensors": [{"data": [], "name": sensor.name, "sensor_id": sensor.sensor_id}],
        }

    def test_esp8266__only_esp8266_sensors(self):
        """Test that only ESP8266 sensors are included, not DS18B20."""
        esp8266_sensor = SensorFactory(type=SensorType.ESP8266, is_active=True, sensor_id="esp8266_1")
        now = timezone.now()
        SensorLogFactory(sensor_id=esp8266_sensor.sensor_id, created_at=now)

        ds18b20_sensor = SensorFactory(type=SensorType.DS18B20, is_active=True, sensor_id="ds18b20_1")
        SensorLogFactory(sensor_id=ds18b20_sensor.sensor_id, created_at=now)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 1
        assert response.data["sensors"][0]["sensor_id"] == "esp8266_1"

    def test_esp8266__only_active_sensors(self):
        """Test that only active sensors are included."""
        active_sensor = SensorFactory(type=SensorType.ESP8266, is_active=True, sensor_id="active_1")
        inactive_sensor = SensorFactory(type=SensorType.ESP8266, is_active=False, sensor_id="inactive_1")
        now = timezone.now()
        SensorLogFactory(sensor_id=active_sensor.sensor_id, created_at=now)
        SensorLogFactory(sensor_id=inactive_sensor.sensor_id, created_at=now)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 1
        assert response.data["sensors"][0]["sensor_id"] == "active_1"

    def test_esp8266__only_last_12_hours(self):
        """Test that only logs from the last 12 hours are included."""
        sensor = SensorFactory(type=SensorType.ESP8266, is_active=True, sensor_id="sensor_1")
        now = timezone.now()

        recent_log_time = now - timedelta(hours=6)
        SensorLogFactory(sensor_id=sensor.sensor_id, created_at=recent_log_time, temp=22.5)

        old_log_time = now - timedelta(hours=13)
        SensorLogFactory(sensor_id=sensor.sensor_id, created_at=old_log_time, temp=21.0)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 1
        assert len(response.data["timestamps"]) > 0
        sensor_data = response.data["sensors"][0]
        assert 22.5 in sensor_data["data"]

    def test_esp8266__data_structure(self):
        """Test that the response has the correct data structure."""
        sensor = SensorFactory(type=SensorType.ESP8266, is_active=True, sensor_id="sensor_1", name="Test ESP8266")
        now = timezone.now()
        SensorLogFactory(sensor_id=sensor.sensor_id, created_at=now, temp=22.5)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        assert "timestamps" in response.data
        assert "sensors" in response.data
        assert isinstance(response.data["timestamps"], list)
        assert isinstance(response.data["sensors"], list)

        if response.data["sensors"]:
            sensor_data = response.data["sensors"][0]
            assert "sensor_id" in sensor_data
            assert "name" in sensor_data
            assert "data" in sensor_data
            assert sensor_data["sensor_id"] == "sensor_1"
            assert sensor_data["name"] == "Test ESP8266"
            assert isinstance(sensor_data["data"], list)
            assert len(response.data["timestamps"]) == len(sensor_data["data"])

    def test_esp8266__multiple_sensors_and_logs(self):
        """Test with multiple sensors and multiple logs."""
        sensor1 = SensorFactory(type=SensorType.ESP8266, is_active=True, sensor_id="esp8266_1", name="ESP8266 1")
        sensor2 = SensorFactory(type=SensorType.ESP8266, is_active=True, sensor_id="esp8266_2", name="ESP8266 2")

        now = timezone.now()
        SensorLogFactory(sensor_id=sensor1.sensor_id, created_at=now - timedelta(hours=2), temp=22.0)
        SensorLogFactory(sensor_id=sensor1.sensor_id, created_at=now - timedelta(hours=1), temp=22.5)

        SensorLogFactory(sensor_id=sensor2.sensor_id, created_at=now - timedelta(hours=1), temp=23.0)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["sensors"]) == 2

        sensor_ids = [s["sensor_id"] for s in response.data["sensors"]]
        assert "esp8266_1" in sensor_ids
        assert "esp8266_2" in sensor_ids


@pytest.mark.django_db
class TestChartOptionsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:chart-options")

    def test_chart_options__ds18b20(self):
        """Test that DS18B20 chart options are returned correctly."""
        response = self.client.get(self.url, {"type": "ds18b20"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["y_min"] == 20
        assert response.data["y_max"] == 45
        assert response.data["time_unit"] == "minute"
        assert response.data["time_tooltip_format"] == "ll HH:mm"

    def test_chart_options__esp8266(self):
        """Test that ESP8266 chart options are returned correctly."""
        response = self.client.get(self.url, {"type": "esp8266"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["y_min"] == 18
        assert response.data["y_max"] == 32
        assert response.data["time_unit"] == "minute"
        assert response.data["time_tooltip_format"] == "ll HH:mm"

    def test_chart_options__missing_type(self):
        """Test that missing type parameter returns 400."""
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_chart_options__invalid_type(self):
        """Test that invalid type parameter returns 400."""
        response = self.client.get(self.url, {"type": "invalid"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_chart_options__not_allowed_methods(self, method):
        """Test that only GET method is allowed."""
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
