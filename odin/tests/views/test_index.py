from unittest.mock import patch

import pytest

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from odin.tests.factories import SensorFactory, VoltageLogFactory, WeatherFactory


@pytest.mark.django_db
@pytest.mark.views
class TestIndexView:
    @patch("odin.apps.core.services.subprocess.run")
    def test_index(self, mock_subprocess, client):
        # Mock systemctl calls
        mock_subprocess.return_value.stdout = b"active"

        response = client.get(reverse("index"), follow=True)
        assert response.status_code == status.HTTP_200_OK

    @patch("odin.apps.core.services.subprocess.run")
    def test_index_uses_cached_context(self, mock_subprocess, client):
        # Mock systemctl calls
        mock_subprocess.return_value.stdout = b"active"

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
