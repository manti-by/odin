from unittest.mock import patch

import pytest

from odin.apps.core.models import Device
from odin.apps.core.webpush import send_push_notification_to_admins
from odin.tests.factories import DeviceFactory


@pytest.mark.django_db
class TestSendPushNotificationToAdmins:
    def setup_method(self):
        self.admin_device = DeviceFactory(is_admin=True)
        self.non_admin_device = DeviceFactory(is_admin=False)

    @patch("odin.apps.core.webpush.send_push_notification")
    def test_send_push_notification_to_admins_sends_to_admin_devices_only(self, mock_send_push):
        send_push_notification_to_admins(title="Test Title", body="Test Body")

        mock_send_push.assert_called_once_with(
            device=self.admin_device,
            title="Test Title",
            body="Test Body",
            icon=None,
            badge=None,
        )

    @patch("odin.apps.core.webpush.send_push_notification")
    def test_send_push_notification_to_admins_with_multiple_admins(self, mock_send_push):
        admin_device_2 = DeviceFactory(is_admin=True)

        send_push_notification_to_admins(title="Alert", body="Warning")

        assert mock_send_push.call_count == 2

        calls = mock_send_push.call_args_list
        assert calls[0][1]["device"] == self.admin_device
        assert calls[1][1]["device"] == admin_device_2

    @patch("odin.apps.core.webpush.send_push_notification")
    def test_send_push_notification_to_admins_with_custom_icon_and_badge(self, mock_send_push):
        send_push_notification_to_admins(
            title="Custom",
            body="Message",
            icon="/custom/icon.png",
            badge="/custom/badge.png",
        )

        mock_send_push.assert_called_once_with(
            device=self.admin_device,
            title="Custom",
            body="Message",
            icon="/custom/icon.png",
            badge="/custom/badge.png",
        )

    @patch("odin.apps.core.webpush.send_push_notification")
    def test_send_push_notification_to_admins_with_no_admins(self, mock_send_push):
        Device.objects.filter(is_admin=True).delete()

        send_push_notification_to_admins(title="Test", body="Test")

        mock_send_push.assert_not_called()

    @patch("odin.apps.core.webpush.send_push_notification")
    def test_send_push_notification_to_admins_handles_send_failure(self, mock_send_push):
        mock_send_push.side_effect = Exception("Push failed")

        with pytest.raises(Exception, match="Push failed"):
            send_push_notification_to_admins(title="Test", body="Test")
