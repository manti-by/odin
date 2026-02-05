from unittest.mock import MagicMock, patch

import pytest

from django.test import override_settings

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestFetchTrafficCommand:
    @override_settings(UNET_USERNAME="testuser", UNET_PASSWORD="testpass")
    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver")
    def test_fetch_traffic_creates_record(self, mock_webdriver):
        from odin.apps.provider.management.commands.fetch_traffic import Command

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "mb;1500"

        mock_driver = MagicMock()
        mock_webdriver.Chrome.return_value = mock_driver
        mock_driver.find_element.return_value = mock_element

        mock_wait = MagicMock()
        mock_webdriver.support.ui.WebDriverWait.return_value = mock_wait

        Command().handle()
        assert Traffic.objects.exists()

    @override_settings(UNET_USERNAME="", UNET_PASSWORD="")
    def test_fetch_traffic_handles_missing_credentials(self):
        from odin.apps.provider.management.commands.fetch_traffic import Command

        Command().handle()
        assert Traffic.objects.count() == 0
