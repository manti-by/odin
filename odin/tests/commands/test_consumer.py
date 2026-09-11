import json
from unittest.mock import MagicMock, patch

import pytest

from django.conf import settings

from odin.apps.relays.models import RelayState
from odin.apps.sensors.models import SensorLog
from odin.tests.factories import RelayFactory


@pytest.mark.django_db
class TestConsumeSensorsCommand:
    def setup_method(self):
        from odin.apps.core.management.commands.consumer import Command

        self.command = Command()

    def test_process_message__creates_sensor_log(self):
        message = {
            "type": "SENSOR_DATA_UPDATE",
            "data": {"sensor_id": "sensor_1", "temp": 21.5, "humidity": 40},
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

        self.command.process_message(json.dumps(message).encode())

        log = SensorLog.objects.get(sensor_id="sensor_1")
        assert log.temp == 21.5
        assert log.humidity == 40

    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_state", return_value={"state": RelayState.ON.value})
    def test_process_message__refreshes_relay_state(self, mock_get_relay_state: MagicMock):
        RelayFactory(relay_id="PUMP-1")
        message = {
            "type": "RELAY_STATE_UPDATE",
            "data": {"relay_id": "PUMP-1", "state": RelayState.ON.value},
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

        self.command.process_message(json.dumps(message).encode())

        mock_get_relay_state.assert_called_once_with("PUMP-1")

    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_state")
    def test_process_message__ignores_unknown_relay(self, mock_get_relay_state: MagicMock):
        message = {
            "type": "RELAY_STATE_UPDATE",
            "data": {"relay_id": "unknown", "state": RelayState.ON.value},
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

        self.command.process_message(json.dumps(message).encode())

        mock_get_relay_state.assert_not_called()

    def test_process_message__relay_missing_relay_id(self):
        message = {"type": "RELAY_STATE_UPDATE", "data": {"state": RelayState.ON.value}}

        self.command.process_message(json.dumps(message).encode())

    def test_process_message__ignores_unknown_type(self):
        message = {"type": "SOMETHING_ELSE", "data": {}}

        self.command.process_message(json.dumps(message).encode())

        assert SensorLog.objects.count() == 0

    def test_process_message__ignores_malformed_payload(self):
        self.command.process_message(b"not valid json")

        assert SensorLog.objects.count() == 0

    @patch("odin.apps.core.management.commands.consumer.signal.signal")
    @patch("odin.apps.core.management.commands.consumer.RedisBus.get_redis")
    def test_handle__subscribes_to_sensor_and_relay_channels(self, mock_get_redis: MagicMock, mock_signal: MagicMock):
        pubsub = MagicMock()
        mock_get_redis.return_value.pubsub.return_value = pubsub
        self.command.running = False

        self.command.handle()

        pubsub.subscribe.assert_called_once_with(settings.REDIS_SENSORS_CHANNEL, settings.REDIS_RELAYS_CHANNEL)
