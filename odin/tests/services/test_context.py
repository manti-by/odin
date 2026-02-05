from unittest.mock import patch

import pytest

from django.core.cache import cache

from odin.apps.core.services import (
    build_index_context,
    get_cached_index_context,
    set_cached_index_context,
    update_index_context_cache,
)
from odin.tests.factories import SensorFactory, TrafficFactory, VoltageLogFactory, WeatherFactory


@pytest.mark.django_db
class TestIndexContextServices:
    @patch("odin.apps.core.services.subprocess.run")
    def test_build_index_context_returns_dict(self, mock_subprocess):
        # Mock systemctl calls
        mock_subprocess.return_value.stdout = b"active"

        SensorFactory(is_active=True)
        VoltageLogFactory()
        WeatherFactory()
        TrafficFactory()

        context = build_index_context()

        assert isinstance(context, dict)
        assert "weather" in context
        assert "sensors" in context
        assert "voltage" in context
        assert "error_logs" in context
        assert "systemd_status" in context
        assert "traffic" in context

    def test_set_and_get_cached_index_context(self):
        test_context = {"test_key": "test_value"}

        set_cached_index_context(test_context)
        result = get_cached_index_context()

        assert result == test_context

    def test_get_cached_index_context_returns_none_when_not_set(self):
        set_cached_index_context(None)
        result = get_cached_index_context()
        assert result is None

    @patch("odin.apps.core.services.subprocess.run")
    def test_update_index_context_cache(self, mock_subprocess):
        # Mock systemctl calls
        mock_subprocess.return_value.stdout = b"active"

        SensorFactory(is_active=True)
        VoltageLogFactory()
        WeatherFactory()
        TrafficFactory()

        with patch.object(cache, "set") as mock_set:
            update_index_context_cache()
            mock_set.assert_called_once()

    @patch("odin.apps.core.services.subprocess.run")
    def test_build_index_context_includes_traffic(self, mock_subprocess):
        # Mock systemctl calls
        mock_subprocess.return_value.stdout = b"active"

        SensorFactory(is_active=True)
        VoltageLogFactory()
        WeatherFactory()
        traffic = TrafficFactory()

        context = build_index_context()

        assert context["traffic"] == traffic
