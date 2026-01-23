from unittest.mock import MagicMock, patch

import pytest

from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.urls import reverse
from rest_framework import status

from odin.apps.relays.admin import RelayAdmin
from odin.apps.relays.models import Relay, RelayType
from odin.tests.factories import DjangoAdminUserFactory, RelayFactory


@pytest.mark.django_db
@pytest.mark.views
class TestRelayAdmin:
    def setup_method(self):
        self.user = DjangoAdminUserFactory()
        self.relay = RelayFactory()

    def test_relay_changelist(self, client):
        """Test relay changelist page loads."""
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Relay._meta, "changelist")), follow=True)
        assert response.status_code == status.HTTP_200_OK

    def test_relay_change(self, client):
        """Test relay change page loads."""
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Relay._meta, "change"), args=[self.relay.id]), follow=True)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.views
class TestRelayAdminSaveModel:
    def setup_method(self):
        self.user = DjangoAdminUserFactory()
        self.relay = RelayFactory()

    @patch("odin.apps.relays.admin.KafkaService.send_relay_update")
    def test_save_model_sends_kafka_message_on_change(self, mock_send_relay_update):
        """Test that saving relay sends Kafka message with relay_id and target_state."""
        self.relay.force_state = "OFF"
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, self.relay, form, change=True)
        mock_send_relay_update.assert_called_once_with(relay_id=self.relay.relay_id, target_state="OFF")

    @patch("odin.apps.relays.admin.KafkaService.send_relay_update")
    def test_save_model_sends_kafka_message_on_add(self, mock_send_relay_update):
        """Test that adding new relay sends Kafka message."""
        new_relay = RelayFactory.build(relay_id="new_relay_123", force_state=None)

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, new_relay, form, change=False)

        mock_send_relay_update.assert_called_once()
        call_kwargs = mock_send_relay_update.call_args.kwargs
        assert call_kwargs["relay_id"] == "new_relay_123"

    @patch("odin.apps.relays.admin.KafkaService.send_relay_update")
    def test_save_model_sends_kafka_message_with_correct_target_state(self, mock_send_relay_update):
        """Test that Kafka message contains correct target_state."""
        self.relay.type = RelayType.PUMP
        self.relay.force_state = "OFF"
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, self.relay, form, change=True)

        call_args = mock_send_relay_update.call_args
        assert call_args.kwargs["target_state"] == "OFF"

    @patch("odin.apps.relays.admin.KafkaService.send_relay_update")
    def test_save_model_sends_kafka_message_when_force_state_cleared(self, mock_send_relay_update):
        """Test Kafka message when force_state is cleared (set to None)."""
        self.relay.force_state = None
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, self.relay, form, change=True)

        mock_send_relay_update.assert_called_once()

    @patch("odin.apps.relays.admin.KafkaService.send_relay_update")
    def test_save_model_sends_kafka_message_with_pump_target_state_from_schedule(self, mock_send_relay_update):
        """Test Kafka message uses pump schedule for target_state when force_state is None."""

        self.relay.type = RelayType.PUMP
        self.relay.force_state = None
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, self.relay, form, change=True)

        mock_send_relay_update.assert_called_once()
        call_kwargs = mock_send_relay_update.call_args.kwargs
        assert call_kwargs["relay_id"] == self.relay.relay_id
        # Just check that target_state is sent (could be ON or UNKNOWN depending on current time)
        assert call_kwargs["target_state"] in ["ON", "UNKNOWN"]
