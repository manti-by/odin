from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.core.redis_bus import RedisBus
from odin.apps.relays.models import RelayMode, RelayState, RelayType
from odin.apps.sensors.models import Sensor, SensorType
from odin.tests.factories import RelayFactory, SensorFactory, SensorLogFactory


@pytest.mark.django_db
class TestEsp8266DashboardAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:esp8266-dashboard")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_esp8266_dashboard__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_esp8266_dashboard__empty(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"is_alive": True, "sensors": []}

    def test_esp8266_dashboard__only_active_and_visible(self):
        SensorFactory(type=SensorType.ESP8266, sensor_id="esp1", is_active=True, is_visible=True)
        SensorFactory(type=SensorType.ESP8266, sensor_id="esp2", is_active=True, is_visible=False)
        SensorFactory(type=SensorType.ESP8266, sensor_id="esp3", is_active=False, is_visible=True)
        SensorFactory(type=SensorType.DS18B20, sensor_id="ds1", is_active=True, is_visible=True)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor_ids = [sensor["sensor_id"] for sensor in response.data["sensors"]]
        assert sensor_ids == ["esp1"]

    def test_esp8266_dashboard__relay_and_alive_flag(self):
        relay = RelayFactory(relay_id="rel1", context={"state": "ON"})
        sensor = SensorFactory(type=SensorType.ESP8266, sensor_id="esp1", relay=relay, is_visible=True)
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())

        with patch.object(RedisBus, "get_relay_latest_message", return_value={"data": {"state": "ON"}}):
            response = self.client.get(self.url, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_alive"] is True

        sensor = response.data["sensors"][0]
        assert sensor["relay"]["relay_id"] == "rel1"
        assert sensor["relay"]["state"] == "ON"
        assert sensor["relay"]["is_on"] is True

    def test_esp8266_dashboard__not_alive_when_sensor_is_stale(self):
        sensor = SensorFactory(type=SensorType.ESP8266, sensor_id="esp1", is_visible=True)
        Sensor.objects.filter(pk=sensor.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        sensor.refresh_from_db()
        assert sensor.is_alive is False

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_alive"] is False


@pytest.mark.django_db
class TestDs18B20DashboardAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:ds18b20-dashboard")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_ds18b20_dashboard__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_ds18b20_dashboard__empty(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"is_alive": True, "sensors": []}

    def test_ds18b20_dashboard__splits_by_type(self):
        SensorFactory(type=SensorType.ESP8266, sensor_id="esp1", is_visible=True)
        SensorFactory(type=SensorType.DS18B20, sensor_id="ds1", is_visible=True)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor_ids = [sensor["sensor_id"] for sensor in response.data["sensors"]]
        assert sensor_ids == ["ds1"]

    def test_ds18b20_dashboard__linked_sensor(self):
        linked = SensorFactory(sensor_id="linked1", type=SensorType.DS18B20, is_visible=True)
        SensorLogFactory(sensor=linked, temp=Decimal("25.0"), created_at=timezone.now())
        SensorFactory(
            type=SensorType.DS18B20,
            sensor_id="ds1",
            linked_sensor=linked,
            is_visible=True,
        )

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensor = next(s for s in response.data["sensors"] if s["sensor_id"] == "ds1")
        assert sensor["linked_sensor"]["sensor_id"] == "linked1"
        assert sensor["linked_sensor"]["temp"] == "25.00"

    def test_ds18b20_dashboard__relay_mode_computed_on_read(self):
        """Relay mode is recomputed on read so the tile never shows a stale mode."""
        pump = RelayFactory(relay_id="pump1", type=RelayType.PUMP, state=RelayState.OFF)
        servo = RelayFactory(relay_id="servo1", type=RelayType.SERVO, related_relay=pump, mode=RelayMode.MIDSEASON)
        sensor = SensorFactory(type=SensorType.DS18B20, sensor_id="ds1", relay=servo, is_visible=True)
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())

        with patch.object(RedisBus, "get_relay_latest_message", return_value={"data": {"state": "OFF"}}):
            response = self.client.get(self.url, format="json")

        assert response.status_code == status.HTTP_200_OK
        relay = response.data["sensors"][0]["relay"]
        assert relay["mode"] == RelayMode.IGNORED
