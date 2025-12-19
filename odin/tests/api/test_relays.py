import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.relays.models import Relay
from odin.tests.factories import RelayFactory


@pytest.mark.django_db
class TestRelaysView:
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
