from decimal import Decimal
from unittest.mock import patch

import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.relays.models import Relay, RelayMode, RelayState, RelayType
from odin.apps.sensors.models import Sensor
from odin.tests.factories import RelayFactory, SensorFactory, SensorLogFactory


@pytest.mark.django_db
class TestRelaysAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:relays:list")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_relays__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_relays__list(self):
        sensor = RelayFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        for field in ("relay_id", "name", "type"):
            assert field in response.data["results"][0]
            assert getattr(sensor, field) == response.data["results"][0][field]

        RelayFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_relays__list_empty(self):
        """Test that list returns an empty result when no relays exist."""
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert response.data["results"] == []

    def test_relays__list_only_active(self):
        """Test that list returns only active relays."""
        active_relay = RelayFactory(is_active=True)
        RelayFactory(is_active=False)
        RelayFactory(is_active=False)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["relay_id"] == active_relay.relay_id

    def test_relays__list_different_types(self):
        """Test that list returns relays of all types."""
        pump_relay = RelayFactory(type=RelayType.PUMP)
        servo_relay = RelayFactory(type=RelayType.SERVO)
        valve_relay = RelayFactory(type=RelayType.VALVE)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

        relay_ids = [r["relay_id"] for r in response.data["results"]]
        assert pump_relay.relay_id in relay_ids
        assert servo_relay.relay_id in relay_ids
        assert valve_relay.relay_id in relay_ids

    def test_relays__response_fields(self):
        """Test that response includes all expected fields."""
        RelayFactory(relay_id="test_relay", name="Test Relay", type=RelayType.PUMP)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        relay_data = response.data["results"][0]
        expected_fields = {"relay_id", "name", "type", "state", "target_state", "created_at"}
        assert expected_fields.issubset(set(relay_data.keys()))
        assert relay_data["relay_id"] == "test_relay"
        assert relay_data["name"] == "Test Relay"
        assert relay_data["type"] == RelayType.PUMP


@pytest.mark.django_db
class TestRelaysRetrieveAPI:
    def setup_method(self):
        self.client = APIClient()
        self.relay: Relay = RelayFactory()  # noqa
        self.url = reverse("api:v1:relays:retrieve_update", args=(self.relay.relay_id,))

    def test_relays__retrieve(self):
        """Test retrieving a single relay."""
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["relay_id"] == self.relay.relay_id
        assert response.data["name"] == self.relay.name
        assert response.data["type"] == self.relay.type

    def test_relays__retrieve_includes_target_state(self):
        """Test that retrieve response includes target_state field."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "target_state" in response.data

    def test_relays__retrieve_includes_context(self):
        """Test that retrieve response returns the relay context."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["context"]["schedule"]["periods"] == [
            {"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}
        ]

    def test_relays__retrieve_computes_mode_on_read(self):
        """Mode is recomputed on read so a stale stored mode is never returned."""
        pump: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF)
        relay: Relay = RelayFactory(type=RelayType.SERVO, related_relay=pump, mode=RelayMode.MIDSEASON)
        sensor: Sensor = SensorFactory(relay_id=relay.relay_id)
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("23.0"), created_at=timezone.now())

        url = reverse("api:v1:relays:retrieve_update", args=(relay.relay_id,))
        response = self.client.get(url, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["mode"] == RelayMode.IGNORED

    def test_relays__retrieve_non_existent(self):
        """Test that retrieve returns 404 for non-existent relay."""
        url = reverse("api:v1:relays:retrieve_update", args=("non_existent_id",))
        response = self.client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRelaysUpdateAPI:
    def setup_method(self):
        self.client = APIClient()
        self.relay: Relay = RelayFactory(type=RelayType.PUMP, force_state=None)  # noqa
        self.url = reverse("api:v1:relays:retrieve_update", args=(self.relay.relay_id,))

    @staticmethod
    def _schedule(*periods: dict) -> dict:
        return {"context": {"schedule": {"periods": list(periods)}}}

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule(self, mock_publish):
        """Test that a schedule update persists periods into the relay context."""
        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        self.relay.refresh_from_db()
        assert self.relay.context["schedule"]["periods"] == [
            {"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}
        ]
        mock_publish.assert_called_once_with(relay_id=self.relay.relay_id, state=self.relay.state)

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule_replaces_existing_schedule(self, mock_publish):
        """Test that a new schedule replaces the previously stored periods."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "20:00", "end_time": "22:00", "target_state": "OFF"}),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        self.relay.refresh_from_db()
        assert self.relay.context["schedule"]["periods"] == [
            {"start_time": "20:00", "end_time": "22:00", "target_state": "OFF"}
        ]

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule_preserves_unrelated_context(self, mock_publish):
        """Test that updating a schedule keeps unrelated context keys."""
        self.relay.context = {"existing_key": "existing_value"}
        self.relay.save()

        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        self.relay.refresh_from_db()
        assert self.relay.context["existing_key"] == "existing_value"

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule_recomputes_target_state(self, mock_publish):
        """Test that a schedule update recomputes and persists state and mode."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "00:00", "end_time": "00:01", "target_state": "OFF"}),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        self.relay.refresh_from_db()
        assert self.relay.state in (RelayState.ON, RelayState.OFF)
        assert self.relay.mode is not None

    def test_relays__update_schedule_rejects_invalid_time(self):
        """Test that malformed times are rejected."""
        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "8:00", "end_time": "18:00", "target_state": "ON"}),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_relays__update_schedule_rejects_zero_duration_period(self):
        """Test that a period with equal start and end times is rejected."""
        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "08:00", "target_state": "ON"}),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_relays__update_schedule_rejects_more_than_5_periods(self):
        """Test that more than five periods are rejected."""
        periods = [
            {"start_time": f"{hour:02d}:00", "end_time": f"{hour:02d}:30", "target_state": "ON"} for hour in range(6)
        ]
        response = self.client.patch(self.url, data=self._schedule(*periods), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "periods",
        (
            (
                {"start_time": "08:00", "end_time": "12:00", "target_state": "ON"},
                {"start_time": "11:00", "end_time": "13:00", "target_state": "OFF"},
            ),
            (
                {"start_time": "22:00", "end_time": "06:00", "target_state": "ON"},
                {"start_time": "05:00", "end_time": "08:00", "target_state": "OFF"},
            ),
            (
                {"start_time": "08:00", "end_time": "18:00", "target_state": "ON"},
                {"start_time": "09:00", "end_time": "10:00", "target_state": "OFF"},
            ),
        ),
    )
    def test_relays__update_schedule_rejects_overlapping_periods(self, periods):
        """Test that overlapping periods are rejected, including overnight spans."""
        response = self.client.patch(self.url, data=self._schedule(*periods), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule_allows_adjacent_periods(self, mock_publish):
        """Test that periods only touching at their boundaries are allowed."""
        response = self.client.patch(
            self.url,
            data=self._schedule(
                {"start_time": "08:00", "end_time": "12:00", "target_state": "ON"},
                {"start_time": "12:00", "end_time": "18:00", "target_state": "OFF"},
            ),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_relays__update_schedule_requires_target_state_for_pump(self):
        """Test that PUMP periods without target_state are rejected."""
        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00"}),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule_requires_target_temp_for_servo(self, mock_publish):
        """Test that SERVO periods without target_temp are rejected."""
        self.relay.type = RelayType.SERVO
        self.relay.save()

        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00"}),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule_accepts_target_temp_for_servo(self, mock_publish):
        """Test that SERVO periods with target_temp are accepted."""
        self.relay.type = RelayType.SERVO
        self.relay.save()

        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00", "target_temp": 24.5}),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        self.relay.refresh_from_db()
        assert self.relay.context["schedule"]["periods"][0]["target_temp"] == 24.5

    def test_relays__update_schedule_rejects_valve_relay(self):
        """Test that periods are rejected for VALVE relays (no actionable target)."""
        self.relay.type = RelayType.VALVE
        self.relay.save()

        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00"}),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_schedule_allows_clearing_for_valve(self, mock_publish):
        """Test that clearing an existing schedule on a VALVE relay is still allowed."""
        self.relay.type = RelayType.VALVE
        self.relay.context = {"schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00"}]}}
        self.relay.save()

        response = self.client.patch(self.url, data=self._schedule(), format="json")
        assert response.status_code == status.HTTP_200_OK
        mock_publish.assert_not_called()

        self.relay.refresh_from_db()
        assert self.relay.context["schedule"]["periods"] == []

    def test_relays__update_non_existent_relay(self):
        """Test that update returns 404 for non-existent relay."""
        url = reverse("api:v1:relays:retrieve_update", args=("non_existent_id",))
        response = self.client.patch(
            url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}),
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=True)
    def test_relays__update_with_empty_context(self, mock_publish):
        """Test that update with empty context dict works."""
        self.relay.context = {"existing_key": "existing_value"}
        self.relay.save()

        response = self.client.patch(self.url, data={"context": {}}, format="json")
        assert response.status_code == status.HTTP_200_OK

        self.relay.refresh_from_db()
        # Empty context should preserve existing context (update, not replace)
        assert "existing_key" in self.relay.context

    @patch("odin.api.v1.relays.views.RedisBus.publish_relay_control", return_value=False)
    def test_relays__update_schedule_logs_publish_failure(self, mock_publish):
        """Test that a Redis publish failure does not fail the request."""
        response = self.client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}),
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        mock_publish.assert_called_once()

    def test_relays__update_requires_authentication(self):
        """Test that schedule updates require an authenticated session."""
        client = APIClient()
        response = client.patch(
            self.url,
            data=self._schedule({"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}),
            format="json",
        )
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
