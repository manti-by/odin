from decimal import Decimal

import pytest

from odin.apps.provider.models import Traffic
from odin.tests.factories import TrafficFactory


@pytest.mark.django_db
class TestTrafficModel:
    def setup_method(self):
        self.traffic = TrafficFactory()

    def test_traffic_str_representation(self):
        expected = f"{self.traffic.value} {self.traffic.unit} ({self.traffic.created_at})"
        assert str(self.traffic) == expected

    def test_traffic_created_with_correct_values(self):
        assert isinstance(self.traffic.value, Decimal)
        assert isinstance(self.traffic.unit, str)
        assert self.traffic.created_at is not None

    def test_traffic_manager_latest_returns_most_recent(self):
        Traffic.objects.all().delete()
        old_traffic = TrafficFactory()
        new_traffic = TrafficFactory()

        latest = Traffic.objects.latest()

        assert latest == new_traffic
        assert latest != old_traffic

    def test_traffic_manager_latest_returns_none_when_empty(self):
        Traffic.objects.all().delete()
        latest = Traffic.objects.latest()
        assert latest is None

    def test_traffic_ordering_is_by_created_at_desc(self):
        Traffic.objects.all().delete()
        traffic1 = TrafficFactory()
        traffic2 = TrafficFactory()
        traffic3 = TrafficFactory()

        traffic_list = list(Traffic.objects.all())

        assert traffic_list == [traffic3, traffic2, traffic1]
