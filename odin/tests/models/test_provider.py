from decimal import Decimal

import pytest

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestTrafficModel:
    def test_traffic_creation(self):
        traffic = Traffic.objects.create(value=Decimal("100.50"), unit="MB")
        assert traffic.value == Decimal("100.50")
        assert traffic.unit == "MB"
        assert traffic.created_at is not None

    def test_traffic_str(self):
        traffic = Traffic.objects.create(value=Decimal("50.25"), unit="GB")
        assert "50.25" in str(traffic)
        assert "GB" in str(traffic)

    def test_traffic_ordering(self):
        traffic1 = Traffic.objects.create(value=Decimal("10"), unit="MB")
        traffic2 = Traffic.objects.create(value=Decimal("20"), unit="MB")
        traffic3 = Traffic.objects.create(value=Decimal("30"), unit="MB")
        traffic_list = list(Traffic.objects.all())
        assert traffic_list[0] == traffic3
        assert traffic_list[1] == traffic2
        assert traffic_list[2] == traffic1
