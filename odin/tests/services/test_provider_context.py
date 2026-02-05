import pytest

from odin.apps.core.services import build_index_context
from odin.apps.provider.models import Traffic
from odin.tests.factories import TrafficFactory


@pytest.mark.django_db
class TestProviderContext:
    def test_index_context_includes_traffic(self):
        # Create test traffic data
        traffic = TrafficFactory(value="123.45", unit="GB")
        
        # Build index context
        context = build_index_context()
        
        # Verify traffic is included in context
        assert "traffic" in context
        assert context["traffic"] == traffic
        assert context["traffic"].value == 123.45
        assert context["traffic"].unit == "GB"

    def test_index_context_without_traffic(self):
        # Build index context without any traffic data
        context = build_index_context()
        
        # Verify traffic is None when no data exists
        assert "traffic" in context
        assert context["traffic"] is None

    def test_index_context_with_multiple_traffic_entries(self):
        # Create multiple traffic entries
        old_traffic = TrafficFactory(value="100.00", unit="GB")
        new_traffic = TrafficFactory(value="200.00", unit="GB")
        
        # Build index context
        context = build_index_context()
        
        # Verify the latest traffic (by created_at) is included
        assert "traffic" in context
        assert context["traffic"] == new_traffic
        assert context["traffic"].value == 200.00