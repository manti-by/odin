import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.conf import settings

from odin.apps.relays.models import Relay, RelayState
from odin.apps.sensors.models import SensorLog
from odin.tests.factories import RelayFactory, SensorFactory, UserFactory


@pytest.mark.django_db
class TestConsumeSensorsCommand:
    def setup_method(self):
        from odin.apps.core.management.commands.consumer import Command

        self.command = Command()

    def test_process_message__creates_sensor_log(self):
        sensor = SensorFactory(sensor_id="sensor_1")
        message = {
            "type": "SENSOR_DATA_UPDATE",
            "data": {"sensor_id": "sensor_1", "temp": 21.5, "humidity": 40},
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

        self.command.process_message(json.dumps(message).encode())

        log = SensorLog.objects.get()
        assert log.sensor == sensor
        assert log.temp == 21.5
        assert log.humidity == 40

        sensor.refresh_from_db()
        assert sensor.temp == Decimal("21.5")
        assert sensor.humidity == Decimal("40")

    def _relay_message(self, relay_id: str = "PUMP-1", state: str = RelayState.ON.value, **extra) -> bytes:
        return json.dumps(
            {
                "type": "RELAY_STATE_UPDATE",
                "data": {"relay_id": relay_id, "state": state, **extra},
                "timestamp": "2026-01-01T00:00:00+00:00",
            }
        ).encode()

    def test_process_message__applies_state_and_creates_log(self):
        relay = RelayFactory(relay_id="PUMP-1", state=RelayState.OFF)

        self.command.process_message(self._relay_message())

        relay.refresh_from_db()
        assert relay.state == RelayState.ON
        log = relay.logs.first()
        assert log is not None
        assert log.old_state == RelayState.OFF
        assert log.new_state == RelayState.ON

    def test_process_message__attributes_log_to_message_user(self):
        user = UserFactory()
        relay = RelayFactory(relay_id="PUMP-1", state=RelayState.OFF)

        self.command.process_message(self._relay_message(user_id=user.pk))

        log = relay.logs.first()
        assert log is not None
        assert log.updated_by == user

    def test_process_message__falls_back_to_system_user(self):
        """A message without user_id is attributed to settings.REDIS_BUS_USER_ID."""
        user = UserFactory()
        RelayFactory(relay_id="PUMP-1", state=RelayState.OFF)

        with patch.object(settings, "REDIS_BUS_USER_ID", user.pk):
            self.command.process_message(self._relay_message())

        assert Relay.objects.get(relay_id="PUMP-1").logs.first().updated_by == user

    def test_process_message__ignores_unknown_relay(self):
        self.command.process_message(self._relay_message(relay_id="unknown"))

        assert Relay.objects.filter(relay_id="unknown").count() == 0

    def test_process_message__ignores_invalid_state(self):
        relay = RelayFactory(relay_id="PUMP-1", state=RelayState.OFF)

        self.command.process_message(self._relay_message(state="BROKEN"))

        relay.refresh_from_db()
        assert relay.state == RelayState.OFF
        assert relay.logs.count() == 0

    def test_process_message__relay_missing_relay_id(self):
        message = {"type": "RELAY_STATE_UPDATE", "data": {"state": RelayState.ON.value}}

        self.command.process_message(json.dumps(message).encode())

    def test_process_message__relay_missing_state(self):
        relay = RelayFactory(relay_id="PUMP-1", state=RelayState.OFF)
        message = {"type": "RELAY_STATE_UPDATE", "data": {"relay_id": "PUMP-1"}}

        self.command.process_message(json.dumps(message).encode())

        relay.refresh_from_db()
        assert relay.state == RelayState.OFF
        assert relay.logs.count() == 0

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
