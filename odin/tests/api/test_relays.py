import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.relays.models import Relay, RelayType
from odin.tests.factories import RelayFactory


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

    def test_relays__update(self):
        relay: Relay = RelayFactory()  # noqa
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

        url = reverse("api:v1:relays:update", args=(relay.relay_id,))
        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_200_OK

        relay.refresh_from_db()
        assert relay.context["state"] == "ON"

    def test_relays__list_empty(self):
        """Test that list returns empty result when no relays exist."""
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

    def test_relays__update_with_existing_context(self):
        """Test that update merges with existing context."""
        relay = RelayFactory(context={"existing_key": "existing_value", "state": "OFF"})
        url = reverse("api:v1:relays:update", args=(relay.relay_id,))

        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_200_OK

        relay.refresh_from_db()
        assert relay.context["state"] == "ON"
        assert relay.context["existing_key"] == "existing_value"

    def test_relays__update_different_states(self):
        """Test updating relay to different state values."""
        relay = RelayFactory()
        url = reverse("api:v1:relays:update", args=(relay.relay_id,))

        # Test ON state
        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_200_OK
        relay.refresh_from_db()
        assert relay.context["state"] == "ON"
        assert relay.state == "ON"

        # Test OFF state
        response = self.client.patch(url, data={"context": {"state": "OFF"}}, format="json")
        assert response.status_code == status.HTTP_200_OK
        relay.refresh_from_db()
        assert relay.context["state"] == "OFF"
        assert relay.state == "OFF"

        # Test custom state
        response = self.client.patch(url, data={"context": {"state": "STANDBY"}}, format="json")
        assert response.status_code == status.HTTP_200_OK
        relay.refresh_from_db()
        assert relay.context["state"] == "STANDBY"
        assert relay.state == "STANDBY"

    def test_relays__update_non_existent_relay(self):
        """Test that update returns 404 for non-existent relay."""
        url = reverse("api:v1:relays:update", args=("non_existent_id",))
        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_relays__update_with_empty_context(self):
        """Test that update with empty context dict works."""
        relay = RelayFactory(context={"existing_key": "existing_value"})
        url = reverse("api:v1:relays:update", args=(relay.relay_id,))

        response = self.client.patch(url, data={"context": {}}, format="json")
        assert response.status_code == status.HTTP_200_OK

        relay.refresh_from_db()
        # Empty context should preserve existing context (update, not replace)
        assert "existing_key" in relay.context

    def test_relays__response_fields(self):
        """Test that response includes all expected fields."""
        RelayFactory(relay_id="test_relay", name="Test Relay", type=RelayType.PUMP)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        relay_data = response.data["results"][0]
        expected_fields = {"relay_id", "name", "type", "context", "created_at"}
        assert expected_fields.issubset(set(relay_data.keys()))
        assert relay_data["relay_id"] == "test_relay"
        assert relay_data["name"] == "Test Relay"
        assert relay_data["type"] == RelayType.PUMP

    def test_relays__state_property(self):
        """Test that relay state property works correctly."""
        # Relay without state in context should return UNKNOWN
        relay = RelayFactory(context={})
        assert relay.state == "UNKNOWN"

        # Relay with state in context should return that state
        relay = RelayFactory(context={"state": "ON"})
        assert relay.state == "ON"

        relay.context["state"] = "OFF"
        relay.save()
        relay.refresh_from_db()
        assert relay.state == "OFF"
