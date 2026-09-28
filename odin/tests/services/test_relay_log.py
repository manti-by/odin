from unittest.mock import MagicMock, patch

import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.relays.admin import RelayAdmin
from odin.apps.relays.models import Relay, RelayLog, RelayMode, RelayState, RelayType
from odin.apps.relays.services import RelayLogService
from odin.tests.factories import DjangoAdminUserFactory, RelayFactory, UserFactory


@pytest.mark.django_db
class TestRelayLogService:
    def setup_method(self) -> None:
        self.relay: Relay = RelayFactory(
            type=RelayType.PUMP,
            state=RelayState.OFF,
            mode=RelayMode.BASIC,
            force_state=None,
            context={},
        )

    def test__logs_state_change(self):
        before = RelayLogService.snapshot(self.relay)
        self.relay.state = RelayState.ON
        self.relay.save()

        log = RelayLogService(self.relay).log_change(before)

        assert log is not None
        assert log.relay == self.relay
        assert log.old_state == RelayState.OFF
        assert log.new_state == RelayState.ON

    @pytest.mark.parametrize(
        ("field", "value"),
        (
            ("state", RelayState.ON),
            ("mode", RelayMode.FORCED),
            ("force_state", RelayState.ON),
        ),
    )
    def test__logs_each_tracked_field(self, field, value):
        """Any single tracked field change is enough to create a log row."""
        before = RelayLogService.snapshot(self.relay)
        setattr(self.relay, field, value)
        self.relay.save()

        log = RelayLogService(self.relay).log_change(before)

        assert log is not None
        assert getattr(log, f"new_{field}") == value

    def test__logs_context_change(self):
        schedule = {"schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}}
        before = RelayLogService.snapshot(self.relay)
        self.relay.context = schedule
        self.relay.save()

        log = RelayLogService(self.relay).log_change(before)

        assert log is not None
        assert log.old_context == {}
        assert log.new_context == schedule

    def test__context_snapshot_is_deep_copied(self):
        """In-place context mutations are detected because the snapshot is copied."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()
        before = RelayLogService.snapshot(self.relay)

        self.relay.context["schedule"]["periods"][0]["target_state"] = "OFF"
        self.relay.save()
        log = RelayLogService(self.relay).log_change(before)

        assert log is not None
        assert log.old_context["schedule"]["periods"][0]["target_state"] == "ON"
        assert log.new_context["schedule"]["periods"][0]["target_state"] == "OFF"

    def test__no_change__returns_none(self):
        before = RelayLogService.snapshot(self.relay)

        assert RelayLogService(self.relay).log_change(before) is None
        assert RelayLog.objects.count() == 0

    def test__none_to_on_transition(self):
        self.relay.state = None
        self.relay.save()
        before = RelayLogService.snapshot(self.relay)

        self.relay.state = RelayState.ON
        self.relay.save()
        log = RelayLogService(self.relay).log_change(before)

        assert log is not None
        assert log.old_state is None
        assert log.new_state == RelayState.ON

    def test__stores_updated_by_when_user_supplied(self):
        user = UserFactory()
        before = RelayLogService.snapshot(self.relay)
        self.relay.state = RelayState.ON
        self.relay.save()

        log = RelayLogService(self.relay, user=user).log_change(before)

        assert log is not None
        assert log.updated_by == user

    def test__updated_by_defaults_to_none(self):
        before = RelayLogService.snapshot(self.relay)
        self.relay.state = RelayState.ON
        self.relay.save()

        log = RelayLogService(self.relay).log_change(before)

        assert log is not None
        assert log.updated_by is None

    def test__log_survives_relay_deletion(self):
        """Deleting a relay must not destroy its audit history."""
        before = RelayLogService.snapshot(self.relay)
        self.relay.state = RelayState.ON
        self.relay.save()
        log = RelayLogService(self.relay).log_change(before)
        assert log is not None

        self.relay.delete()

        log.refresh_from_db()
        assert log.relay is None
        assert RelayLog.objects.filter(pk=log.pk).exists()


@pytest.mark.django_db
class TestRelayLogApplyTargetState:
    def test__apply_target_state_creates_log(self):
        relay: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF, mode=RelayMode.FALLBACK)
        relay.context = {"schedule": {"periods": [{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}]}}
        relay.save()

        assert relay.apply_target_state() == RelayState.ON

        log = relay.logs.first()
        assert log is not None
        assert log.old_state == RelayState.OFF
        assert log.new_state == RelayState.ON

    def test__apply_target_state_no_change__no_log(self):
        relay: Relay = RelayFactory(
            type=RelayType.PUMP, force_state=RelayState.ON, state=RelayState.ON, mode=RelayMode.FORCED
        )

        assert relay.apply_target_state() == RelayState.ON
        assert relay.logs.count() == 0

    def test__apply_target_state_stores_user(self):
        user = UserFactory()
        relay: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF)
        relay.context = {"schedule": {"periods": [{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}]}}
        relay.save()

        relay.apply_target_state(user=user)

        assert relay.logs.first().updated_by == user

    def test__target_state_property_is_pure(self):
        """Reading the property must not persist state/mode nor append an audit row."""
        relay: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF, mode=RelayMode.FALLBACK)
        relay.context = {"schedule": {"periods": [{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}]}}
        relay.save()

        assert relay.target_state == RelayState.ON
        assert relay.state == RelayState.OFF
        assert relay.mode == RelayMode.FALLBACK
        assert relay.logs.count() == 0


@pytest.mark.django_db
class TestRelayLogRefreshState:
    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_latest_message")
    def test__refresh_state_updates_state_but_never_logs(self, mock_get_state: MagicMock) -> None:
        """Reconciliation refreshes (consumer wake-ups, SPA polling) must never audit.

        ``relays:control`` carries both ODIN's own control echo (whose persisted
        key is still stale) and Coruscant's ack, so logging here would record a
        phantom reversion that never physically happened.
        """
        relay: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF)
        mock_get_state.return_value = {"data": {"state": "ON"}}

        assert relay.refresh_state() == RelayState.ON
        assert relay.logs.count() == 0


@pytest.mark.django_db
class TestRelayLogAdmin:
    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control", return_value=True)
    def test__admin_save_model_creates_log(self, mock_publish: MagicMock) -> None:
        user = DjangoAdminUserFactory()
        relay: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF, force_state=None)

        request = MagicMock()
        request.user = user
        form = MagicMock()
        form.data = {}
        relay.force_state = RelayState.ON

        RelayAdmin(Relay, None).save_model(request, relay, form, change=True)

        log = relay.logs.first()
        assert log is not None
        assert log.old_force_state is None
        assert log.new_force_state == RelayState.ON
        assert log.updated_by == user

    @patch("odin.apps.relays.admin.RedisBus.publish_relay_control", return_value=True)
    def test__admin_noop_save_attributes_recompute_to_system(self, mock_publish: MagicMock) -> None:
        """A save that changes no tracked field logs the schedule-driven transition as system."""
        user = DjangoAdminUserFactory()
        relay: Relay = RelayFactory(
            type=RelayType.PUMP, state=RelayState.OFF, mode=RelayMode.FALLBACK, force_state=None
        )
        relay.context = {"schedule": {"periods": [{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}]}}
        relay.save()

        request = MagicMock()
        request.user = user
        form = MagicMock()
        form.data = {}

        RelayAdmin(Relay, None).save_model(request, relay, form, change=True)

        log = relay.logs.first()
        assert log is not None
        assert log.new_state == RelayState.ON
        assert log.updated_by is None


@pytest.mark.django_db
class TestRelayLogAPI:
    def setup_method(self) -> None:
        self.client = APIClient()
        self.relay: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF, force_state=None)
        self.url = reverse("api:v1:relays:retrieve_update", args=(self.relay.relay_id,))

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test__api_update_creates_log(self, mock_publish: MagicMock) -> None:
        response = self.client.patch(self.url, data={"force_state": "ON"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        log = self.relay.logs.first()
        assert log is not None
        assert log.old_force_state is None
        assert log.new_force_state == RelayState.ON
        assert log.updated_by is not None

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test__api_update_no_change__no_log(self, mock_publish: MagicMock) -> None:
        """An update that leaves every tracked field untouched writes no log row."""
        self.relay.state = RelayState.OFF
        self.relay.mode = RelayMode.FORCED
        self.relay.force_state = RelayState.OFF
        self.relay.save()

        response = self.client.patch(self.url, data={"force_state": "OFF"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert self.relay.logs.count() == 0
