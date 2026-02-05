import factory.fuzzy
from factory import DictFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyDecimal

from django.contrib.auth.models import User

from odin.apps.core.models import Device
from odin.apps.electricity.models import VoltageLog
from odin.apps.provider.models import Traffic
from odin.apps.relays.models import Relay
from odin.apps.sensors.models import Sensor, SensorLog, SensorType
from odin.apps.weather.models import Weather


DEFAULT_USER_PASSWORD = "pa55word"  # noqa


class TestFactory(DictFactory):
    name = factory.Faker("pybool")
    int_field = factory.Faker("pyint")
    char_field = factory.Faker("word")
    choice_field = factory.fuzzy.FuzzyChoice(("ONE", "TWO"))
    datetime_field_start = factory.Faker("past_date")
    datetime_field_stop = factory.Faker("past_date")


class UserFactory(DjangoModelFactory):
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", DEFAULT_USER_PASSWORD)

    class Meta:
        model = User


class DjangoAdminUserFactory(UserFactory):
    is_superuser = True


class LogDataFactory(DictFactory):
    name = factory.Faker("name")
    msg = factory.Faker("sentence")
    filename = factory.Faker("word")
    levelname = factory.Faker("word")
    asctime = factory.Faker("date_time")


class RelayFactory(DjangoModelFactory):
    relay_id = factory.Faker("word")
    type = SensorType.ESP8266
    name = factory.Faker("name")
    is_active = True

    class Meta:
        model = Relay


class SensorFactory(DjangoModelFactory):
    sensor_id = factory.Faker("word")
    type = SensorType.ESP8266
    name = factory.Faker("name")
    is_active = True

    class Meta:
        model = Sensor


class SensorLogFactory(DjangoModelFactory):
    sensor_id = factory.Faker("word")
    temp = FuzzyDecimal(low=-10, high=40, precision=2)
    humidity = FuzzyDecimal(low=0, high=100, precision=2)
    created_at = factory.Faker("date_time")

    class Meta:
        model = SensorLog


class SensorLogDataFactory(DictFactory):
    sensor_id = factory.Faker("word")
    temp = FuzzyDecimal(low=-10, high=40, precision=2)
    humidity = FuzzyDecimal(low=0, high=100, precision=2)
    created_at = factory.Faker("date_time")


class VoltageLogFactory(DjangoModelFactory):
    voltage = FuzzyDecimal(low=200, high=260, precision=2)

    class Meta:
        model = VoltageLog


class WeatherDataFactory(factory.DictFactory):
    temp = str(FuzzyDecimal(low=-10, high=40, precision=2))
    pressure = str(FuzzyDecimal(low=670, high=810, precision=2))
    humidity = str(FuzzyDecimal(low=0, high=100, precision=2))


class WeatherFactory(DjangoModelFactory):
    external_id = factory.Faker("word")
    data = WeatherDataFactory()
    period = factory.Faker("date_time")

    class Meta:
        model = Weather


class DeviceFactory(DjangoModelFactory):
    subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test_endpoint",
        "expirationTime": None,
        "keys": {
            "p256dh": "BEl62iUYgU3x1PReSkf7G1c8OEQ8L6L5KxV3J5YvQqA=",
            "auth": "test_auth_token",
        },
    }
    browser = "chrome"
    is_active = True

    class Meta:
        model = Device


class TrafficFactory(DjangoModelFactory):
    value = FuzzyDecimal(low=0, high=1000, precision=2)
    unit = factory.fuzzy.FuzzyChoice(("GB", "MB", "TB"))

    class Meta:
        model = Traffic
