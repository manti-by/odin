import factory.fuzzy

from factory.django import DjangoModelFactory

from db_benchmarks.core.models import (
    PlainModel,
    IndexedModel,
    OptimizedModel,
    StatusChoices,
)


class PlainModelFactory(DjangoModelFactory):
    class Meta:
        model = PlainModel

    boolean_field = factory.Faker("pybool")
    int_field = factory.Faker("pyint")
    char_field = factory.Faker("word")
    choice_field = factory.fuzzy.FuzzyChoice(StatusChoices.values)
    datetime_field_start = factory.Faker("past_date")
    datetime_field_stop = factory.Faker("past_date")


class IndexedModelFactory(PlainModelFactory):
    class Meta:
        model = IndexedModel


class OptimizedModelFactory(PlainModelFactory):
    class Meta:
        model = OptimizedModel
