from unittest.mock import DEFAULT, MagicMock, patch

import pytest

from django.test import override_settings

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestFetchTrafficCommand:
    @override_settings(UNET_USERNAME="testuser", UNET_PASSWORD="testpass")
    @patch.multiple(
        "odin.apps.provider.management.commands.fetch_traffic",
        webdriver=DEFAULT,
        WebDriverWait=DEFAULT,
        Options=DEFAULT,
        expected_conditions=DEFAULT,
    )
    def test_fetch_traffic_creates_record(self, **mocks):
        from odin.apps.provider.management.commands.fetch_traffic import Command

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "mb;1500"
        mock_element.send_keys.return_value = None
        mock_element.click.return_value = None

        mock_driver = MagicMock()
        mocks["webdriver"].Chrome.return_value = mock_driver
        mock_driver.get.return_value = None
        mock_driver.find_element.return_value = mock_element
        mock_driver.quit.return_value = None

        # Mock WebDriverWait to complete immediately without waiting
        mock_wait_instance = MagicMock()
        mock_wait_instance.until.return_value = mock_element
        mocks["WebDriverWait"].return_value = mock_wait_instance

        Command().handle()
        assert Traffic.objects.exists()

    @override_settings(UNET_USERNAME="", UNET_PASSWORD="")
    def test_fetch_traffic_handles_missing_credentials(self):
        from odin.apps.provider.management.commands.fetch_traffic import Command

        Command().handle()
        assert Traffic.objects.count() == 0
