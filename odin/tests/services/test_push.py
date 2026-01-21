from unittest.mock import MagicMock, patch

import pytest

from odin.apps.core.push import send_broadcast_notification, send_push_notification
from odin.tests.factories import DeviceFactory


@pytest.mark.django_db
class TestSendPushNotification:
    def test_send_push_notification_success(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        device = DeviceFactory()
        mock_webpush = MagicMock()
        with patch("odin.apps.core.push.WebPush", return_value=mock_webpush):
            result = send_push_notification(device, "Test Title", "Test Body")
            assert result is True
            mock_webpush.send.assert_called_once()

    def test_send_push_notification_with_custom_options(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        device = DeviceFactory()
        mock_webpush = MagicMock()
        with patch("odin.apps.core.push.WebPush", return_value=mock_webpush):
            result = send_push_notification(
                device,
                "Alert",
                "Temperature too high",
                icon="/custom/icon.png",
                badge="/custom/badge.png",
                tag="temp_alert",
                url="/sensors/",
                data={"sensor_id": "abc123"},
            )
            assert result is True
            mock_webpush.send.assert_called_once()

    def test_send_push_notification_failure(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        device = DeviceFactory()
        from webpush import WebPushException

        mock_webpush = MagicMock()
        mock_webpush.send.side_effect = WebPushException("Push failed")
        with patch("odin.apps.core.push.WebPush", return_value=mock_webpush):
            result = send_push_notification(device, "Test", "Body")
            assert result is False

    def test_send_push_notification_uses_default_icons(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        device = DeviceFactory()
        mock_webpush = MagicMock()
        with patch("odin.apps.core.push.WebPush", return_value=mock_webpush):
            send_push_notification(device, "Title", "Body")
            call_kwargs = mock_webpush.send.call_args[1]
            assert "payload" in call_kwargs
            payload = call_kwargs["payload"]
            assert payload["icon"] == "/static/favicon-128.png"
            assert payload["badge"] == "/static/favicon-32.png"


@pytest.mark.django_db
class TestSendBroadcastNotification:
    def test_broadcast_notification_success(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        DeviceFactory(is_active=True)
        DeviceFactory(is_active=True)
        DeviceFactory(is_active=False)

        mock_webpush = MagicMock()
        with patch("odin.apps.core.push.WebPush", return_value=mock_webpush):
            success, failure = send_broadcast_notification("Broadcast", "Hello all!")
            assert success == 2
            assert failure == 0
            assert mock_webpush.send.call_count == 2

    def test_broadcast_notification_marks_inactive_on_failure(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        active_device = DeviceFactory(is_active=True)
        from webpush import WebPushException

        mock_webpush = MagicMock()
        mock_webpush.send.side_effect = WebPushException("Failed")
        with patch("odin.apps.core.push.WebPush", return_value=mock_webpush):
            success, failure = send_broadcast_notification("Alert", "Check sensors")
            assert success == 0
            assert failure == 1

        active_device.refresh_from_db()
        assert active_device.is_active is False

    def test_broadcast_notification_empty_recipients(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        success, failure = send_broadcast_notification("No one", "to receive")
        assert success == 0
        assert failure == 0

    def test_broadcast_notification_with_custom_data(self, settings):
        settings.VAPID_PRIVATE_KEY = "private_key"
        settings.VAPID_PUBLIC_KEY = "public_key"
        settings.VAPID_ADMIN_EMAIL = "mailto:test@example.com"

        DeviceFactory(is_active=True)

        mock_webpush = MagicMock()
        with patch("odin.apps.core.push.WebPush", return_value=mock_webpush):
            send_broadcast_notification(
                "Warning",
                "High temperature",
                data={"temp": 45.5, "location": "boiler_room"},
                tag="temp_warning",
                url="/sensors/boiler/",
            )
            call_kwargs = mock_webpush.send.call_args[1]
            assert "payload" in call_kwargs
            payload = call_kwargs["payload"]
            assert payload["data"]["temp"] == 45.5
            assert payload["data"]["location"] == "boiler_room"
            assert payload["tag"] == "temp_warning"
            assert payload["url"] == "/sensors/boiler/"
