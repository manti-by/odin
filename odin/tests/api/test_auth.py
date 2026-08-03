from unittest.mock import patch

import pytest

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from odin.apps.sensors.models import Sensor
from odin.tests.factories import AuthFactory, RelayFactory, SensorFactory, UserFactory


@pytest.mark.django_db
class TestApplicationServerKeyView:
    """VAPID public key endpoint is public (AllowAny) for PWA push registration."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:app-server-key")

    def test_public_access_returns_200(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_token_returns_403(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid_token")
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_valid_token_returns_200(self):
        auth = AuthFactory()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {auth.token}")
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCsrfTokenEndpoint:
    """The SPA bootstraps its csrftoken cookie by GETting this endpoint."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:csrf")

    def test_csrf__returns_200(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "CSRF cookie set"

    def test_csrf__sets_cookie(self):
        response = self.client.get(self.url, format="json")
        assert "csrftoken" in response.cookies


@pytest.mark.django_db
class TestWriteEndpointsAuth:
    """Anonymous (no credentials) writes should be rejected."""

    def setup_method(self):
        self.client = APIClient()

    def test_sensors_update__anonymous_returns_403(self):
        sensor: Sensor = SensorFactory()  # noqa
        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))
        response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_relays_update__anonymous_returns_403(self):
        relay = RelayFactory()
        url = reverse("api:v1:relays:retrieve_update", args=(relay.relay_id,))
        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCsrfEnforcement:
    """Session-authenticated unsafe requests without X-CSRFToken should fail."""

    def setup_method(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_sensors_update__without_csrf_returns_403(self):
        sensor: Sensor = SensorFactory()  # noqa
        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))
        response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sensors_update__with_csrf_returns_200(self):
        sensor: Sensor = SensorFactory()  # noqa
        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))

        # Bootstrap the CSRF cookie
        csrf_url = reverse("api:v1:core:csrf")
        self.client.get(csrf_url, format="json")

        # Read the csrf token from the cookies set
        csrf_token = self.client.cookies.get("csrftoken")
        assert csrf_token is not None, "CSRF cookie should be present"

        response = self.client.patch(
            url,
            data={"context": {"target_temp": "25.5"}},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token.value,
        )
        assert response.status_code == status.HTTP_200_OK

    def test_relays_update__without_csrf_returns_403(self):
        relay = RelayFactory()
        url = reverse("api:v1:relays:retrieve_update", args=(relay.relay_id,))
        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_relays_update__with_csrf_returns_200(self):
        relay = RelayFactory()
        url = reverse("api:v1:relays:retrieve_update", args=(relay.relay_id,))

        csrf_url = reverse("api:v1:core:csrf")
        self.client.get(csrf_url, format="json")
        csrf_token = self.client.cookies.get("csrftoken")

        response = self.client.patch(
            url,
            data={"context": {"state": "ON"}},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token.value,
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTokenAuthCsrfBypass:
    """Token-authenticated requests are CSRF-exempt by DRF design."""

    def setup_method(self):
        self.client = APIClient(enforce_csrf_checks=True)
        auth = AuthFactory()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {auth.token}")

    def test_sensors_update__token_no_csrf_returns_200(self):
        sensor: Sensor = SensorFactory()  # noqa
        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))
        response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_relays_update__token_no_csrf_returns_200(self):
        relay = RelayFactory()
        url = reverse("api:v1:relays:retrieve_update", args=(relay.relay_id,))
        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestThrottling:
    """Write endpoints are throttled per DRF scope."""

    THROTTLED_RATES = {"sensors_update": "2/min", "relays_update": "2/min"}

    def setup_method(self):
        self.client = APIClient()
        auth = AuthFactory()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {auth.token}")
        cache.clear()

    @patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"sensors_update": "2/min", "relays_update": "2/min"})
    def test_sensors_update__throttles_after_limit(self):
        sensor: Sensor = SensorFactory()  # noqa
        url = reverse("api:v1:sensors:update", args=(sensor.sensor_id,))

        for _ in range(2):
            response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
            assert response.status_code == status.HTTP_200_OK

        # Third request should be throttled
        response = self.client.patch(url, data={"context": {"target_temp": "25.5"}}, format="json")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"sensors_update": "2/min", "relays_update": "2/min"})
    def test_relays_update__throttles_after_limit(self):
        relay = RelayFactory()
        url = reverse("api:v1:relays:retrieve_update", args=(relay.relay_id,))

        for _ in range(2):
            response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
            assert response.status_code == status.HTTP_200_OK

        # Third request should be throttled
        response = self.client.patch(url, data={"context": {"state": "ON"}}, format="json")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
