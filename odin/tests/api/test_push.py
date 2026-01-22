import pytest
from webpush import VAPID

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.core.models import Device
from odin.tests.factories import DeviceFactory


@pytest.mark.django_db
class TestVapidAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:vapid")

    def test_vapid__returns_server_key(self, settings):
        keys = VAPID.generate_keys()
        settings.VAPID_SERVER_KEY = keys[2]
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["server_key"] is not None

    def test_vapid__returns_empty_string_when_server_key_not_configured(self, settings):
        settings.VAPID_SERVER_KEY = ""
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["server_key"] == ""

    def test_vapid__post_not_allowed(self):
        response = self.client.post(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestDevicesAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:devices")

    def test_devices__list_returns_count(self):
        DeviceFactory()
        DeviceFactory()
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_devices__list_returns_zero_for_empty(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_devices__list_returns_only_active(self):
        DeviceFactory(is_active=True)
        DeviceFactory(is_active=True)
        DeviceFactory(is_active=False)
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_devices__register_new_device(self):
        subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test_endpoint",
            "expirationTime": None,
            "keys": {
                "p256dh": "BEl62iUYgU3x1PReSkf7G1c8OEQ8L6L5KxV3J5YvQqA=",
                "auth": "test_auth_token",
            },
        }
        data = {"subscription": subscription, "browser": "firefox"}
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        devices = Device.objects.active()
        assert devices.count() == 1
        device = devices.first()
        assert device.subscription == subscription
        assert device.browser == "firefox"
        assert device.is_active is True

    def test_devices__update_existing_device(self):
        existing_device = DeviceFactory(
            subscription={
                "endpoint": "https://example.com/endpoint",
                "keys": {"p256dh": "old_key", "auth": "old_auth"},
            },
            browser="chrome",
            is_active=True,
        )
        subscription = {
            "endpoint": "https://example.com/endpoint",
            "keys": {"p256dh": "updated_key", "auth": "updated_auth"},
        }
        data = {"subscription": subscription, "browser": "safari"}
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        devices = Device.objects.active()
        assert devices.count() == 1
        device = devices.first()
        assert device.id == existing_device.id
        assert device.browser == "safari"
        assert device.subscription["keys"]["p256dh"] == "updated_key"

    def test_devices__register_with_different_endpoint_creates_new(self):
        DeviceFactory(
            subscription={"endpoint": "https://example.com/endpoint1"},
            browser="chrome",
            is_active=True,
        )
        subscription = {
            "endpoint": "https://example.com/endpoint2",
            "keys": {"p256dh": "new_key", "auth": "new_auth"},
        }
        data = {"subscription": subscription}
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        assert Device.objects.active().count() == 2

    def test_devices__register_with_default_browser(self):
        subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/endpoint",
            "keys": {"p256dh": "key", "auth": "auth"},
        }
        data = {"subscription": subscription}
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        device = Device.objects.active().first()
        assert device.browser == "other"

    def test_devices__post_with_missing_subscription(self):
        data = {"browser": "chrome"}
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_devices__get_not_allowed_methods(self):
        response = self.client.put(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = self.client.patch(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = self.client.delete(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
