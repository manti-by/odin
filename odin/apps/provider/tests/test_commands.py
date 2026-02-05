import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from odin.apps.provider.management.commands.update_traffic import Command
from odin.apps.provider.models import Traffic
from odin.tests.factories import TrafficFactory


@pytest.mark.django_db
class TestUpdateTrafficCommand:
    def test_command_without_credentials(self, settings):
        settings.UNET_USERNAME = ""
        settings.UNET_PASSWORD = ""

        command = Command()
        with patch.object(command, "stdout") as mock_stdout:
            command.handle()
            # Should not raise an exception, just log error

    @patch("odin.apps.provider.management.commands.update_traffic.webdriver")
    def test_command_successful_scraping(self, mock_webdriver, settings):
        settings.UNET_USERNAME = "test@example.com"
        settings.UNET_PASSWORD = "password123"

        # Mock selenium components
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        # Mock wait and element finding
        mock_wait = Mock()
        mock_element = Mock()
        mock_element.get_attribute.return_value = "GB;123.45"

        mock_driver.__enter__ = Mock(return_value=mock_driver)
        mock_driver.__exit__ = Mock(return_value=None)

        with patch("odin.apps.provider.management.commands.update_traffic.WebDriverWait", return_value=mock_wait):
            mock_wait.until.return_value = mock_element
            mock_driver.find_element.return_value = mock_element

            command = Command()
            command.handle()

            # Verify traffic was created
            assert Traffic.objects.count() == 1
            traffic = Traffic.objects.first()
            assert traffic.value == Decimal("123.45")
            assert traffic.unit == "GB"

    @patch("odin.apps.provider.management.commands.update_traffic.webdriver")
    def test_command_malformed_data(self, mock_webdriver, settings):
        settings.UNET_USERNAME = "test@example.com"
        settings.UNET_PASSWORD = "password123"

        # Mock selenium components
        mock_driver = Mock()
        mock_webdriver.Chrome.return_value = mock_driver

        # Mock wait and element finding with malformed data
        mock_wait = Mock()
        mock_element = Mock()
        mock_element.get_attribute.return_value = "invalid_format"

        mock_driver.__enter__ = Mock(return_value=mock_driver)
        mock_driver.__exit__ = Mock(return_value=None)

        with patch("odin.apps.provider.management.commands.update_traffic.WebDriverWait", return_value=mock_wait):
            mock_wait.until.return_value = mock_element
            mock_driver.find_element.return_value = mock_element

            command = Command()
            command.handle()

            # Verify no traffic was created due to malformed data
            assert Traffic.objects.count() == 0
