import factory.fuzzy

from factory import DictFactory


class TestFactory(DictFactory):
    name = factory.Faker("pybool")
    int_field = factory.Faker("pyint")
    char_field = factory.Faker("word")
    choice_field = factory.fuzzy.FuzzyChoice(("ONE", "TWO"))
    datetime_field_start = factory.Faker("past_date")
    datetime_field_stop = factory.Faker("past_date")
