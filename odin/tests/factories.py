import factory.fuzzy
from factory import DictFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyDecimal

from django.contrib.auth.models import User

from odin.apps.core.models import Auth, Device
from odin.apps.currency.models import Currency, ExchangeRate
from odin.apps.electricity.models import VoltageLog
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
    username = factory.Sequence(lambda n: f"user_{n}")
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
    stacktrace = None
    variables = None


class RelayFactory(DjangoModelFactory):
    relay_id = factory.Sequence(lambda n: f"relay_{n}")
    type = SensorType.ESP8266
    name = factory.Faker("name")
    is_active = True

    class Meta:
        model = Relay


class SensorFactory(DjangoModelFactory):
    sensor_id = factory.Sequence(lambda n: f"sensor_{n}")
    type = SensorType.ESP8266
    name = factory.Faker("name")
    is_active = True

    class Meta:
        model = Sensor


class SensorLogFactory(DjangoModelFactory):
    sensor = factory.SubFactory(SensorFactory)
    temp = FuzzyDecimal(low=-10, high=40, precision=2)
    humidity = FuzzyDecimal(low=0, high=100, precision=2)
    created_at = factory.Faker("date_time")

    class Meta:
        model = SensorLog

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Persist the log and mirror the ingest pipeline onto its sensor."""
        log = super()._create(model_class, *args, **kwargs)
        if log.sensor:
            log.sensor.update(temp=log.temp, humidity=log.humidity)
        return log


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
    temp = factory.LazyFunction(lambda: {"avg": "22.50"})
    pressure = 750
    humidity = "55"


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


class ExchangeRateFactory(DjangoModelFactory):
    currency = factory.fuzzy.FuzzyChoice(Currency.values)
    rate = FuzzyDecimal(low=1, high=100, precision=4)
    scale = 1
    date = factory.Faker("date")

    class Meta:
        model = ExchangeRate


class AuthFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    token = factory.Sequence(lambda n: f"test_token_{n}")

    class Meta:
        model = Auth
