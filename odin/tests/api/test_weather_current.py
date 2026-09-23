import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.tests.factories import WeatherFactory


@pytest.mark.django_db
class TestWeatherCurrentAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:weather:current")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_weather__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_weather__returns_null_when_no_data(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data is None

    def test_weather__returns_current_weather_fields(self):
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

        assert response.data["temp_display"] == "+22.5"
        assert isinstance(response.data["pressure"], int)
        assert response.data["humidity"] == "55.0"
        assert response.data["wind"]["direction"] == 180
        assert response.data["wind"]["speed"] == "5.0"
        assert response.data["wind"]["gusts"] == "8.0"
        assert response.data["attributes"]["fog"] is True
        assert response.data["attributes"]["snow"] is False
        assert response.data["has_attrs"] is True
