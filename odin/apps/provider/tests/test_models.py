import pytest
from decimal import Decimal

from odin.apps.provider.models import Traffic
from odin.tests.factories import TrafficFactory


@pytest.mark.django_db
class TestTrafficModel:
    def test_traffic_creation(self):
        traffic = TrafficFactory(value=Decimal("123.45"), unit="GB")

        assert Traffic.objects.count() == 1
        assert traffic.value == Decimal("123.45")
        assert traffic.unit == "GB"
        assert "123.45 GB at" in str(traffic)

    def test_traffic_ordering(self):
        traffic1 = TrafficFactory(value=Decimal("100"), unit="MB")
        traffic2 = TrafficFactory(value=Decimal("200"), unit="MB")

        # Should be ordered by -created_at, so latest first
        latest = Traffic.objects.first()
        assert latest == traffic2
