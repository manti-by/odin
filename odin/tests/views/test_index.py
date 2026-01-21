from unittest.mock import patch

import pytest

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from odin.tests.factories import SensorFactory, VoltageLogFactory, WeatherFactory


@pytest.mark.django_db
@pytest.mark.views
class TestIndexView:
    def test_index(self, client):
        response = client.get(reverse("index"), follow=True)
        assert response.status_code == status.HTTP_200_OK

    def test_index_uses_cached_context(self, client):
        SensorFactory(is_active=True)
        VoltageLogFactory()
        WeatherFactory()

        with patch.object(cache, "get") as mock_get:
            mock_get.return_value = {
                "weather": None,
                "sensors": [],
                "home_sensors_is_alive": True,
                "boiler_sensors_is_alive": True,
                "error_logs": [],
                "voltage": None,
                "voltage_chart": "",
                "voltage_values": [],
            }
            response = client.get(reverse("index"), follow=True)
            assert response.status_code == 200
