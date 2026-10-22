from decimal import Decimal

import pytest

from odin.apps.weather.services import apparent_temp


@pytest.mark.parametrize(
    ("temp", "humidity", "wind_speed", "expected"),
    (
        ("12", "80", "1", "10.9960"),
        ("12", "80", "5", "8.1960"),
        ("16", "85", "1", "16.3890"),
        ("16", "85", "5", "13.5890"),
        ("8", "80", "10", "-0.1719"),
        ("-5", "80", "5", "-11.3879"),
    ),
)
def test_apparent_temp__matches_steadman_index(temp, humidity, wind_speed, expected):
    result = apparent_temp(Decimal(temp), Decimal(humidity), Decimal(wind_speed))

    assert result is not None
    assert result.quantize(Decimal("0.0001")) == Decimal(expected)


def test_apparent_temp__feels_colder_with_wind():
    calm = apparent_temp(Decimal("12"), Decimal("80"), Decimal("1"))
    windy = apparent_temp(Decimal("12"), Decimal("80"), Decimal("5"))

    assert windy < calm


def test_apparent_temp__feels_warmer_with_humidity():
    dry = apparent_temp(Decimal("12"), Decimal("40"), Decimal("1"))
    damp = apparent_temp(Decimal("12"), Decimal("80"), Decimal("1"))

    assert damp > dry


@pytest.mark.parametrize(
    ("temp", "humidity", "wind_speed"),
    (
        (None, Decimal("80"), Decimal("5")),
        (Decimal("12"), None, Decimal("5")),
        (Decimal("12"), Decimal("80"), None),
        (None, None, None),
    ),
)
def test_apparent_temp__returns_none_when_an_input_is_missing(temp, humidity, wind_speed):
    """The relay gate falls back to the raw temperature whenever a weather field is missing."""
    assert apparent_temp(temp, humidity, wind_speed) is None
