import pytest

from odin.apps.provider.models import Traffic
from odin.tests.factories import TrafficFactory


@pytest.mark.django_db
class TestTrafficModel:
    def test_traffic_creation(self):
        traffic = TrafficFactory(value="123.45", unit="GB")
        assert traffic.value == 123.45
        assert traffic.unit == "GB"
        assert str(traffic) == "123.45 GB"

    def test_traffic_ordering(self):
        traffic1 = TrafficFactory(value="100.00", unit="GB")
        traffic2 = TrafficFactory(value="200.00", unit="GB")
        
        # Traffic should be ordered by -created_at (newest first)
        traffic_list = Traffic.objects.all()
        assert traffic_list[0] == traffic2
        assert traffic_list[1] == traffic1

    def test_traffic_str_representation(self):
        traffic = TrafficFactory(value="50.75", unit="MB")
        assert str(traffic) == "50.75 MB"