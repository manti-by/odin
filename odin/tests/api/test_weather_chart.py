from datetime import timedelta

import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.tests.factories import WeatherFactory


pytestmark = pytest.mark.django_db


class TestWeatherChartAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:weather-chart")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_weather_chart__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_weather_chart__empty_when_no_data(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "timestamps": [],
            "temp": [],
            "humidity": [],
            "pressure": [],
        }

    def test_weather_chart__returns_three_metrics(self):
        now = timezone.now()
        WeatherFactory(period=now)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "timestamps" in response.data
        assert "temp" in response.data
        assert "humidity" in response.data
        assert "pressure" in response.data
        assert len(response.data["timestamps"]) == 1

    def test_weather_chart__temp_values_are_floats(self):
        now = timezone.now()
        WeatherFactory(period=now)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        temp_values = response.data["temp"]
        assert len(temp_values) == 1
        assert temp_values[0] is None or isinstance(temp_values[0], float)

    def test_weather_chart__pressure_is_hpa(self):
        now = timezone.now()
        WeatherFactory(period=now)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        pressure_values = response.data["pressure"]
        assert len(pressure_values) == 1
        p = pressure_values[0]
        assert p is None or (isinstance(p, int) and 670 <= p <= 810), f"expected hPa value in [670, 810], got {p}"

    def test_weather_chart__timestamps_ascending(self):
        now = timezone.now()
        for hours_ago in [3, 2, 1]:
            WeatherFactory(period=now - timedelta(hours=hours_ago))

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        timestamps = response.data["timestamps"]
        assert timestamps == sorted(timestamps)

    def test_weather_chart__respects_start_param(self):
        now = timezone.now()
        WeatherFactory(period=now - timedelta(hours=1))
        WeatherFactory(period=now)

        start = (now - timedelta(minutes=30)).isoformat()
        response = self.client.get(self.url, {"start": start}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["timestamps"]) == 1

    def test_weather_chart__respects_end_param(self):
        now = timezone.now()
        WeatherFactory(period=now - timedelta(hours=2))
        WeatherFactory(period=now)

        end = (now - timedelta(hours=1)).isoformat()
        response = self.client.get(self.url, {"end": end}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["timestamps"]) == 1

    def test_weather_chart__default_window_48h(self):
        now = timezone.now()
        WeatherFactory(period=now - timedelta(hours=47))
        WeatherFactory(period=now - timedelta(hours=49))

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["timestamps"]) == 1

    def test_weather_chart__multiple_entries(self):
        now = timezone.now()
        for hours_ago in range(5):
            WeatherFactory(period=now - timedelta(hours=hours_ago))

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["timestamps"]) == 5
        assert len(response.data["temp"]) == 5
        assert len(response.data["humidity"]) == 5
        assert len(response.data["pressure"]) == 5

    def test_weather_chart__none_for_missing_metrics(self):
        now = timezone.now()
        WeatherFactory(
            period=now,
            data={"temp": None, "humidity": None, "pressure": None},
        )

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["temp"] == [None]
        assert response.data["humidity"] == [None]
        assert response.data["pressure"] == [None]

    def test_weather_chart__invalid_start_format(self):
        response = self.client.get(self.url, {"start": "not-a-date"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_weather_chart__invalid_end_format(self):
        response = self.client.get(self.url, {"end": "garbage"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
