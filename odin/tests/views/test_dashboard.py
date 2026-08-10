from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from odin.apps.core.models import Log
from odin.apps.core.redis_bus import RedisBus
from odin.apps.currency.models import Currency
from odin.apps.provider.models import Traffic
from odin.apps.sensors.models import SensorType
from odin.tests.factories import (
    ExchangeRateFactory,
    RelayFactory,
    SensorFactory,
    SensorLogFactory,
    VoltageLogFactory,
    WeatherFactory,
)


DEFAULT_SYSTEMD_STATUS = {"scheduler.service": {"status": "active"}, "worker.service": {"error": "mocked"}}


@pytest.mark.django_db
@pytest.mark.views
class TestDashboardAPI:
    def setup_method(self) -> None:
        self.client = APIClient()
        self.url = reverse("api:v1:core:dashboard")
        cache.clear()
        self.systemd_patcher = patch("odin.apps.core.services.systemd_status", return_value=DEFAULT_SYSTEMD_STATUS)
        self.systemd_patcher.start()

    def teardown_method(self) -> None:
        self.systemd_patcher.stop()

    def _make_fake_context(self, **overrides: Any) -> dict:
        base = {
            "weather": None,
            "sensors": [],
            "home_sensors_is_alive": True,
            "boiler_sensors_is_alive": True,
            "error_logs": [],
            "voltage": None,
            "exchange_rates": [],
            "exchange_rates_trends": {},
            "systemd_status": {},
            "traffic": None,
        }
        base.update(overrides)
        return base

    def test_dashboard__ok(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        keys = {
            "weather",
            "sensors",
            "home_sensors_is_alive",
            "boiler_sensors_is_alive",
            "error_logs",
            "voltage",
            "exchange_rates",
            "exchange_rates_trends",
            "systemd_status",
            "traffic",
        }
        assert keys.issubset(response.data.keys())
        assert response.data["sensors"] == {"esp8266": [], "ds18b20": []}
        assert response.data["weather"] is None
        assert response.data["voltage"] is None
        assert response.data["traffic"] is None

    def test_dashboard__weather_fields(self):
        WeatherFactory(
            data={
                "temp": {"avg": "22.5", "min": "18.0", "max": "26.0"},
                "pressure": 760.5,
                "humidity": "55.0",
                "wind": {"direction": 180, "speed": "5.0", "gusts": "8.0"},
                "attributes": {"fog": True, "snow": False, "thunderstorm": False, "black_ice": False},
            },
            period=timezone.now(),
        )

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        w = response.data["weather"]
        assert w["temp_display"] == "+22.5"
        assert isinstance(w["pressure"], int)
        assert w["humidity"] == "55.0"
        assert w["wind"]["direction"] == 180
        assert w["wind"]["speed"] == "5.0"
        assert w["wind"]["gusts"] == "8.0"
        assert w["attributes"]["fog"] is True
        assert w["attributes"]["snow"] is False
        assert w["has_attrs"] is True

    def test_dashboard__sensors_split_by_type(self):
        SensorFactory(type=SensorType.ESP8266, sensor_id="esp1", is_visible=True)
        SensorFactory(type=SensorType.DS18B20, sensor_id="ds1", is_visible=True)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        sensors = response.data["sensors"]
        assert len(sensors["esp8266"]) == 1
        assert sensors["esp8266"][0]["sensor_id"] == "esp1"
        assert len(sensors["ds18b20"]) == 1
        assert sensors["ds18b20"][0]["sensor_id"] == "ds1"

    def test_dashboard__sensor_relay_and_linked_sensor(self):
        RelayFactory(relay_id="rel1", context={"state": "ON"})
        SensorFactory(sensor_id="linked1", type=SensorType.DS18B20, is_visible=True)
        SensorLogFactory(sensor_id="linked1", temp=Decimal("25.0"), created_at=timezone.now())

        SensorFactory(
            type=SensorType.DS18B20,
            sensor_id="ds1",
            relay_id="rel1",
            linked_sensor_id="linked1",
            is_visible=True,
        )

        with patch.object(RedisBus, "get_relay_state", return_value={"state": "ON"}):
            response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        ds = next(s for s in response.data["sensors"]["ds18b20"] if s["sensor_id"] == "ds1")
        assert ds["relay"]["relay_id"] == "rel1"
        assert ds["relay"]["state"] == "ON"
        assert ds["relay"]["is_on"] is True
        assert ds["linked_sensor"]["sensor_id"] == "linked1"
        assert ds["linked_sensor"]["temp"] == "25.00"

    def test_dashboard__exchange_rates_and_trends(self):
        today = date.today()
        yesterday = today - timedelta(days=1)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)
        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=yesterday)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        assert len(response.data["exchange_rates"]) == 1
        assert response.data["exchange_rates"][0]["currency"] == Currency.USD
        assert response.data["exchange_rates"][0]["rate_per_unit"] == "3.2500"
        assert response.data["exchange_rates_trends"]["USD"] is not None

    def test_dashboard__traffic_and_voltage(self):
        Traffic.objects.create(value=Decimal("123.45"), unit="GB")
        VoltageLogFactory(voltage=Decimal("230.50"))

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        assert response.data["traffic"]["value"] == "123.45"
        assert response.data["traffic"]["unit"] == "GB"
        assert response.data["voltage"]["voltage"] == "230.50"

    def test_dashboard__systemd_status(self):
        fake_context = self._make_fake_context(
            systemd_status={"scheduler.service": {"status": "active"}, "worker.service": {"error": "test error"}},
        )
        with patch("odin.api.v1.core.views.update_index_context_cache") as mock_update:
            mock_update.return_value = fake_context
            response = self.client.get(self.url, format="json")

        assert response.status_code == status.HTTP_200_OK
        ss = response.data["systemd_status"]
        assert "scheduler.service" in ss
        assert "worker.service" in ss
        assert ss["worker.service"]["error"] == "test error"

    def test_dashboard__error_logs(self):
        Log.objects.create(
            name="test.stderr",
            msg="Test error message",
            filename="test_module.py",
            levelname="ERROR",
            asctime=timezone.now(),
        )

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        assert len(response.data["error_logs"]) >= 1
        assert response.data["error_logs"][0]["msg"] == "Test error message"

    def test_dashboard__uses_cached_context(self):
        fake_context = self._make_fake_context(boiler_sensors_is_alive=False)
        with patch.object(cache, "get") as mock_get:
            mock_get.return_value = fake_context
            response = self.client.get(self.url, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["home_sensors_is_alive"] is True
        assert response.data["boiler_sensors_is_alive"] is False
        assert response.data["weather"] is None
        assert response.data["sensors"] == {"esp8266": [], "ds18b20": []}
