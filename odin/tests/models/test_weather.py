from decimal import Decimal

import pytest

from odin.apps.weather.models import Weather


def make_weather(data: dict) -> Weather:
    return Weather(data=data)


class TestWeatherHumidity:
    def test_weather__humidity_returns_decimal(self):
        assert make_weather({"humidity": "55"}).humidity == Decimal("55")

    @pytest.mark.parametrize("data", ({}, {"humidity": None}))
    def test_weather__humidity_returns_none_when_missing(self, data):
        assert make_weather(data).humidity is None


class TestWeatherWindSpeed:
    def test_weather__wind_speed_prefers_average_speed(self):
        weather = make_weather({"wind": {"speed": 5, "gusts": 12}})
        assert weather.wind_speed == Decimal(5)

    def test_weather__wind_speed_falls_back_to_gusts(self):
        weather = make_weather({"wind": {"speed": None, "gusts": "12.5"}})
        assert weather.wind_speed == Decimal("12.5")

    def test_weather__wind_speed_keeps_calm_zero(self):
        """A 0 m/s mean speed must not silently fall back to the gusts."""
        weather = make_weather({"wind": {"speed": 0, "gusts": 4}})
        assert weather.wind_speed == Decimal(0)

    @pytest.mark.parametrize("data", ({}, {"wind": None}, {"wind": {"speed": None, "gusts": None}}))
    def test_weather__wind_speed_returns_none_when_missing(self, data):
        assert make_weather(data).wind_speed is None
