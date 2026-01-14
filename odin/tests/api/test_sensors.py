from datetime import timedelta
from decimal import Decimal

import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.sensors.models import Sensor, SensorLog, SensorType
from odin.tests.factories import SensorFactory, SensorLogFactory


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
        """Test that list returns an empty result when no sensors exist."""
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
        sensor: Sensor = SensorFactory(context={"existing_key": "existing_value", "target_temp": "20.0"})  # noqa
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
        sensor: Sensor = SensorFactory(context={"existing_key": "existing_value"})  # noqa
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
        expected_fields = {
            "sensor_id",
            "name",
            "type",
            "context",
            "temp",
            "humidity",
            "temp_offset",
            "humidity_offset",
            "created_at",
        }
        assert expected_fields.issubset(set(sensor_data.keys()))
        assert sensor_data["sensor_id"] == "test_sensor"
        assert sensor_data["name"] == "Test Sensor"
        assert sensor_data["type"] == SensorType.DS18B20

    def test_sensors__response_includes_offset_fields(self):
        """Test that response includes temp_offset and humidity_offset fields."""
        SensorFactory(temp_offset=Decimal("2.5"), humidity_offset=Decimal("5.0"))

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor_data = response.data["results"][0]
        assert sensor_data["temp_offset"] == "2.50"
        assert sensor_data["humidity_offset"] == "5.00"


@pytest.mark.django_db
class TestSensorsModelProperties:
    def test_sensors__target_temp_returns_none_when_not_set(self):
        """Test that target_temp returns None when not in context."""
        sensor: Sensor = SensorFactory(context={})  # noqa
        assert sensor.target_temp is None

    def test_sensors__target_temp_returns_value_from_context(self):
        """Test that target_temp returns value from context."""
        sensor: Sensor = SensorFactory(context={"target_temp": "25.5"})  # noqa
        assert sensor.target_temp == Decimal("25.5")

    def test_sensors__temp_hysteresis_returns_default_when_not_set(self):
        """Test that temp_hysteresis returns default when not in context."""
        sensor: Sensor = SensorFactory(context={})  # noqa
        assert sensor.temp_hysteresis == Decimal("0.5")

    def test_sensors__temp_hysteresis_returns_value_from_context(self):
        """Test that temp_hysteresis returns value from context."""
        sensor: Sensor = SensorFactory(context={"hysteresis": "1.0"})  # noqa
        assert sensor.temp_hysteresis == Decimal("1.0")

    def test_sensors__temp_returns_none_when_no_logs(self):
        """Test that temp returns None when no logs exist."""
        sensor: Sensor = SensorFactory()  # noqa
        assert sensor.temp is None

    def test_sensors__temp_returns_latest_log_temp(self):
        """Test that temp returns temperature from the latest log."""
        sensor: Sensor = SensorFactory()  # noqa
        older_log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("22.5"))  # noqa
        newer_log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("23.5"))  # noqa
        newer_log.created_at = older_log.created_at + timedelta(hours=1)
        newer_log.save()
        assert sensor.temp == Decimal("23.5")

    def test_sensors__humidity_returns_none_when_no_logs(self):
        """Test that humidity returns None when no logs exist."""
        sensor: Sensor = SensorFactory()  # noqa
        assert sensor.humidity is None

    def test_sensors__humidity_returns_latest_log_humidity(self):
        """Test that humidity returns humidity from latest log."""
        sensor: Sensor = SensorFactory()  # noqa
        older_log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, humidity=Decimal("65.0"))  # noqa
        newer_log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, humidity=Decimal("70.0"))  # noqa
        newer_log.created_at = older_log.created_at + timedelta(hours=1)
        newer_log.save()
        assert sensor.humidity == Decimal("70.0")

    def test_sensors__temp_includes_temp_offset(self):
        """Test that temp property includes temp_offset in calculation."""
        sensor: Sensor = SensorFactory(temp_offset=Decimal("2.5"))  # noqa
        log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("20.0"))  # noqa
        assert sensor.temp == Decimal("22.5")

    def test_sensors__temp_with_negative_offset(self):
        """Test that temp property handles negative offset correctly."""
        sensor: Sensor = SensorFactory(temp_offset=Decimal("-1.5"))  # noqa
        log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("25.0"))  # noqa
        assert sensor.temp == Decimal("23.5")

    def test_sensors__humidity_includes_humidity_offset(self):
        """Test that humidity property includes humidity_offset in calculation."""
        sensor: Sensor = SensorFactory(humidity_offset=Decimal("5.0"))  # noqa
        log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, humidity=Decimal("60.0"))  # noqa
        assert sensor.humidity == Decimal("65.0")

    def test_sensors__humidity_with_negative_offset(self):
        """Test that humidity property handles negative offset correctly."""
        sensor: Sensor = SensorFactory(humidity_offset=Decimal("-10.0"))  # noqa
        log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, humidity=Decimal("80.0"))  # noqa
        assert sensor.humidity == Decimal("70.0")

    def test_sensors__zero_offset_does_not_change_value(self):
        """Test that zero offset returns an original value."""
        sensor: Sensor = SensorFactory(temp_offset=Decimal("0.0"), humidity_offset=Decimal("0.0"))  # noqa
        log: SensorLog = SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("22.5"), humidity=Decimal("55.0"))  # noqa
        assert sensor.temp == Decimal("22.5")
        assert sensor.humidity == Decimal("55.0")
