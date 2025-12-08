import factory.fuzzy
from factory import DictFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyDecimal

from django.contrib.auth.models import User

from odin.apps.sensors.models import Sensor, SensorLog, SensorType


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
