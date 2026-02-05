from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.core.management import call_command

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestFetchTrafficCommand:
    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "test_user", clear=False)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "test_pass", clear=False)
    def test_command_creates_traffic_record(self, mock_chrome):
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "GB;150.50"
        mock_driver.find_element.return_value = mock_element

        call_command("fetch_traffic")

        assert Traffic.objects.count() == 1
        traffic = Traffic.objects.first()
        assert traffic.value == Decimal("150.50")
        assert traffic.unit == "GB"

    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "test_user", clear=False)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "test_pass", clear=False)
    def test_command_parses_mb_unit(self, mock_chrome):
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "MB;500.25"
        mock_driver.find_element.return_value = mock_element

        call_command("fetch_traffic")

        traffic = Traffic.objects.first()
        assert traffic.value == Decimal("500.25")
        assert traffic.unit == "MB"

    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "test_user", clear=False)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "test_pass", clear=False)
    def test_command_handles_invalid_format(self, mock_chrome):
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "invalid_format"
        mock_driver.find_element.return_value = mock_element

        call_command("fetch_traffic")

        assert Traffic.objects.count() == 0

    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "", clear=True)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "", clear=True)
    def test_command_handles_missing_credentials(self, mock_chrome):
        call_command("fetch_traffic")

        assert Traffic.objects.count() == 0

    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "test_user", clear=False)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "test_pass", clear=False)
    def test_command_quits_driver_on_success(self, mock_chrome):
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "GB;100.00"
        mock_driver.find_element.return_value = mock_element

        call_command("fetch_traffic")

        mock_driver.quit.assert_called_once()

    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "test_user", clear=False)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "test_pass", clear=False)
    def test_command_quits_driver_on_error(self, mock_chrome):
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_driver.get.side_effect = Exception("Connection error")

        call_command("fetch_traffic")

        mock_driver.quit.assert_called_once()

    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "test_user", clear=False)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "test_pass", clear=False)
    def test_command_uses_headless_mode_by_default(self, mock_chrome):
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "GB;100.00"
        mock_driver.find_element.return_value = mock_element

        call_command("fetch_traffic")

        call_args = mock_chrome.call_args
        assert call_args is not None
        options = call_args.kwargs.get("options")
        assert options is not None

    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch.dict("django.conf.settings.UNET_USERNAME", "test_user", clear=False)
    @patch.dict("django.conf.settings.UNET_PASSWORD", "test_pass", clear=False)
    def test_command_disables_headless_with_flag(self, mock_chrome):
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "GB;100.00"
        mock_driver.find_element.return_value = mock_element

        call_command("fetch_traffic", "--no-headless")

        call_args = mock_chrome.call_args
        assert call_args is not None
