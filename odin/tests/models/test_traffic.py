from decimal import Decimal

import pytest

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestTrafficModel:
    def test_traffic_create_with_value_and_unit(self):
        traffic = Traffic.objects.create(value=Decimal("123.45"), unit="GB")
        assert traffic.value == Decimal("123.45")
        assert traffic.unit == "GB"

    def test_traffic_created_at_is_set(self):
        traffic = Traffic.objects.create(value=Decimal("100.00"), unit="MB")
        assert traffic.created_at is not None

    def test_traffic_str_representation(self):
        traffic = Traffic.objects.create(value=Decimal("50.25"), unit="GB")
        assert str(traffic) == "50.25 GB"

    def test_traffic_ordering_by_created_at_descending(self):
        Traffic.objects.all().delete()
        traffic1 = Traffic.objects.create(value=Decimal("10.00"), unit="GB")
        traffic2 = Traffic.objects.create(value=Decimal("20.00"), unit="GB")
        traffic3 = Traffic.objects.create(value=Decimal("30.00"), unit="GB")

        traffics = Traffic.objects.all()
        assert list(traffics) == [traffic3, traffic2, traffic1]

    def test_traffic_first_returns_latest(self):
        Traffic.objects.all().delete()
        traffic1 = Traffic.objects.create(value=Decimal("10.00"), unit="GB")
        traffic2 = Traffic.objects.create(value=Decimal("20.00"), unit="GB")

        latest = Traffic.objects.first()
        assert latest == traffic2
