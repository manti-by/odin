import pytest
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import override_settings

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestFetchUnetTrafficCommand:
    @override_settings(
        UNET_USERNAME="test_user",
        UNET_PASSWORD="test_pass"
    )
    @patch("odin.apps.provider.management.commands.fetch_unet_traffic.webdriver.Chrome")
    def test_command_with_mock_selenium(self, mock_chrome):
        # Setup mock browser
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Mock find_element calls
        mock_csrf_element = Mock()
        mock_csrf_element.get_attribute.return_value = "test_csrf_token"
        
        mock_username_field = Mock()
        mock_password_field = Mock()
        mock_csrf_field = Mock()
        mock_login_button = Mock()
        
        mock_traffic_span = Mock()
        mock_traffic_span.get_attribute.return_value = "GB;123.45"
        
        # Setup element finding sequence
        mock_driver.find_element.side_effect = [
            mock_csrf_element,  # _csrf_token
            mock_username_field,  # username
            mock_password_field,  # password
            mock_csrf_field,  # _csrf_token
            mock_login_button,  # button[type='submit']
            mock_traffic_span,  # #unet-general-info-box-infobox span[data-units]
        ]
        
        # Call the command
        call_command("fetch_unet_traffic", "--headless")
        
        # Verify traffic was created
        traffic = Traffic.objects.first()
        assert traffic is not None
        assert traffic.value == 123.45
        assert traffic.unit == "GB"
        
        # Verify browser was closed
        mock_driver.quit.assert_called_once()

    @override_settings(
        UNET_USERNAME="",
        UNET_PASSWORD=""
    )
    def test_command_without_credentials(self, capfd):
        # Call command without credentials
        call_command("fetch_unet_traffic")
        
        # Verify no traffic was created
        traffic_count = Traffic.objects.count()
        assert traffic_count == 0
        
        # Verify error message
        captured = capfd.readouterr()
        assert "UNET_USERNAME and UNET_PASSWORD must be set in environment" in captured.err

    @override_settings(
        UNET_USERNAME="test_user",
        UNET_PASSWORD="test_pass"
    )
    @patch("odin.apps.provider.management.commands.fetch_unet_traffic.webdriver.Chrome")
    def test_command_with_no_traffic_data(self, mock_chrome, capfd):
        # Setup mock browser
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Mock find_element calls
        mock_csrf_element = Mock()
        mock_csrf_element.get_attribute.return_value = "test_csrf_token"
        
        mock_username_field = Mock()
        mock_password_field = Mock()
        mock_csrf_field = Mock()
        mock_login_button = Mock()
        
        mock_traffic_span = Mock()
        mock_traffic_span.get_attribute.return_value = ""  # Empty data-units
        
        # Setup element finding sequence
        mock_driver.find_element.side_effect = [
            mock_csrf_element,  # _csrf_token
            mock_username_field,  # username
            mock_password_field,  # password
            mock_csrf_field,  # _csrf_token
            mock_login_button,  # button[type='submit']
            mock_traffic_span,  # #unet-general-info-box-infobox span[data-units]
        ]
        
        # Call the command
        call_command("fetch_unet_traffic", "--headless")
        
        # Verify no traffic was created
        traffic_count = Traffic.objects.count()
        assert traffic_count == 0
        
        # Verify error message
        captured = capfd.readouterr()
        assert "No traffic data found" in captured.err
        
        # Verify browser was closed
        mock_driver.quit.assert_called_once()