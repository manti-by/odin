from datetime import UTC, datetime
from datetime import timezone as dt_timezone
from unittest.mock import MagicMock, patch

import pytest

from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.urls import reverse
from rest_framework import status

from odin.apps.relays.admin import RelayAdmin
from odin.apps.relays.models import Relay, RelayMode, RelayType
from odin.tests.factories import DjangoAdminUserFactory, RelayFactory, create_weather


@pytest.mark.django_db
@pytest.mark.views
class TestRelayAdmin:
    def setup_method(self) -> None:
        self.user = DjangoAdminUserFactory()
        self.relay = RelayFactory()

    def test_relay_changelist(self, client: MagicMock) -> None:
        """Test relay changelist page loads."""
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Relay._meta, "changelist")), follow=True)
        assert response.status_code == status.HTTP_200_OK

    def test_relay_change(self, client: MagicMock) -> None:
        """Test relay change page loads."""
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Relay._meta, "change"), args=[self.relay.id]), follow=True)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.views
class TestRelayAdminSaveModel:
    def setup_method(self) -> None:
        create_weather()
        self.user = DjangoAdminUserFactory()
        self.relay = RelayFactory()

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_publishes_relay_control_on_change(self, mock_publish_relay_control: MagicMock) -> None:
        """Test that saving relay sends Redis message with relay_id and state."""
        self.relay.force_state = "OFF"
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, self.relay, form, change=True)
        mock_publish_relay_control.assert_called_once_with(
            relay_id=self.relay.relay_id, state="OFF", mode=RelayMode.FORCED, user=None
        )

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_publishes_relay_control_on_add(self, mock_publish_relay_control):
        """Test that adding new relay sends Redis message."""
        new_relay = RelayFactory.build(relay_id="new_relay_123", force_state=None)

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, new_relay, form, change=False)

        mock_publish_relay_control.assert_called_once()
        call_kwargs = mock_publish_relay_control.call_args.kwargs
        assert call_kwargs["relay_id"] == "new_relay_123"

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_publishes_relay_control_with_correct_target_state(self, mock_publish_relay_control):
        """Test that Redis message contains correct state."""
        self.relay.type = RelayType.PUMP
        self.relay.force_state = "OFF"
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, self.relay, form, change=True)

        call_args = mock_publish_relay_control.call_args
        assert call_args.kwargs["state"] == "OFF"

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_publishes_relay_control_when_force_state_cleared(self, mock_publish_relay_control):
        """Test Redis message when force_state is cleared (set to None)."""
        self.relay.force_state = None
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)
        form = MagicMock()
        form.data = {}

        admin_instance.save_model(None, self.relay, form, change=True)

        mock_publish_relay_control.assert_called_once()

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_publishes_relay_control_with_pump_target_state_from_schedule(self, mock_publish_relay_control):
        """Test Redis message uses pump schedule for target_state when force_state is None."""

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

        mock_publish_relay_control.assert_called_once()
        call_kwargs = mock_publish_relay_control.call_args.kwargs
        assert call_kwargs["relay_id"] == self.relay.relay_id
        assert call_kwargs["state"] == "ON"


@pytest.mark.django_db
@pytest.mark.views
class TestRelayAdminOverrideSchedule:
    def setup_method(self) -> None:
        create_weather()
        self.user = DjangoAdminUserFactory(is_staff=True)
        self.relay = RelayFactory(type=RelayType.PUMP)

    @staticmethod
    def _form(data: dict[str, str]) -> MagicMock:
        form = MagicMock()
        form.data = data
        return form

    def test_relay_change_renders_override_schedule_component(self, client: MagicMock) -> None:
        """Test that the change page renders the override schedule component with the stored periods."""
        self.relay.context = {
            "override_schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]}
        }
        self.relay.save()

        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Relay._meta, "change"), args=[self.relay.id]))

        content = response.content.decode()
        assert 'id="override-periods-container"' in content
        assert 'id="override-add-period"' in content
        assert 'name="override_schedule-periods-0-start_time" value="08:00"' in content
        assert 'name="override_schedule-periods-0-end_time" value="18:00"' in content
        assert 'name="override_schedule-periods-0-target_state"' in content

    def test_relay_change_renders_no_override_periods_by_default(self, client: MagicMock) -> None:
        """Test that a relay without an override schedule renders an empty override component."""
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Relay._meta, "change"), args=[self.relay.id]))

        content = response.content.decode()
        assert 'id="override-periods-container"' in content
        assert 'name="override_schedule-periods-0-start_time"' not in content

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_stores_override_periods(self, mock_publish_relay_control: MagicMock) -> None:
        """Test that override periods from the admin component land in the relay context."""
        admin_instance = RelayAdmin(Relay, None)
        form = self._form(
            {
                "override_schedule-periods-0-start_time": "08:00",
                "override_schedule-periods-0-end_time": "18:00",
                "override_schedule-periods-0-target_state": "OFF",
            }
        )

        admin_instance.save_model(None, self.relay, form, change=True)

        assert self.relay.context["override_schedule"] == {
            "periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]
        }

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_clears_override_periods_when_all_removed(self, mock_publish_relay_control: MagicMock) -> None:
        """Test that removing every override row empties the stored override schedule."""
        self.relay.context = {
            "override_schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]}
        }
        self.relay.save()

        admin_instance = RelayAdmin(Relay, None)

        admin_instance.save_model(None, self.relay, form=self._form({}), change=True)

        assert self.relay.context["override_schedule"] == {"periods": []}

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_keeps_context_clean_without_override_periods(
        self, mock_publish_relay_control: MagicMock
    ) -> None:
        """Test that a relay without an override schedule does not get an empty override key."""
        admin_instance = RelayAdmin(Relay, None)

        admin_instance.save_model(None, self.relay, form=self._form({}), change=True)

        assert "override_schedule" not in self.relay.context

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_keeps_schedule_and_override_periods_apart(self, mock_publish_relay_control: MagicMock) -> None:
        """Test that both components are parsed independently on one save."""
        admin_instance = RelayAdmin(Relay, None)
        form = self._form(
            {
                "schedule-periods-0-start_time": "05:00",
                "schedule-periods-0-end_time": "07:00",
                "schedule-periods-0-target_state": "ON",
                "override_schedule-periods-0-start_time": "08:00",
                "override_schedule-periods-0-end_time": "18:00",
                "override_schedule-periods-0-target_state": "OFF",
            }
        )

        admin_instance.save_model(None, self.relay, form, change=True)

        assert self.relay.context["schedule"] == {
            "periods": [{"start_time": "05:00", "end_time": "07:00", "target_state": "ON"}]
        }
        assert self.relay.context["override_schedule"] == {
            "periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]
        }

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control")
    def test_save_model_publishes_override_target_state(self, mock_publish_relay_control: MagicMock) -> None:
        """Test that an active override period is published as the recomputed (state, mode) pair."""
        admin_instance = RelayAdmin(Relay, None)
        form = self._form(
            {
                "override_schedule-periods-0-start_time": "08:00",
                "override_schedule-periods-0-end_time": "18:00",
                "override_schedule-periods-0-target_state": "OFF",
            }
        )
        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))

        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            admin_instance.save_model(None, self.relay, form, change=True)

        mock_publish_relay_control.assert_called_once_with(
            relay_id=self.relay.relay_id, state="OFF", mode=RelayMode.OVERRIDE, user=None
        )
