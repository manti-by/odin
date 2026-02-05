from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from odin.apps.core.services import build_index_context
from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestTrafficContext:
    def test_traffic_included_in_index_context(self):
        traffic = Traffic.objects.create(value=Decimal("75.50"), unit="GB")
        context = build_index_context()
        assert context["traffic"] == traffic

    def test_traffic_none_when_no_data(self):
        context = build_index_context()
        assert context["traffic"] is None


@pytest.mark.django_db
class TestFetchTrafficCommand:
    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver")
    def test_fetch_traffic_creates_record(self, mock_webdriver):
        from odin.apps.provider.management.commands.fetch_traffic import Command

        mock_driver = MagicMock()
        mock_webdriver.Chrome.return_value = mock_driver

        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "GB;150.75"

        mock_driver.find_element.return_value = mock_element

        mock_wait = MagicMock()
        mock_webdriver.support.ui.WebDriverWait.return_value = mock_wait

        with patch.object(Traffic.objects, "create") as mock_create:
            mock_create.return_value = Traffic(value=Decimal("150.75"), unit="GB")

            with patch("django.conf.settings") as mock_settings:
                mock_settings.UNET_USERNAME = "testuser"
                mock_settings.UNET_PASSWORD = "testpass"

                cmd = Command()
                cmd.stdout = MagicMock()
                cmd.handle()

                mock_create.assert_called_once_with(value="150.75", unit="GB")

    def test_fetch_traffic_handles_missing_credentials(self):
        from odin.apps.provider.management.commands.fetch_traffic import Command

        with patch("django.conf.settings") as mock_settings:
            mock_settings.UNET_USERNAME = ""
            mock_settings.UNET_PASSWORD = ""

            cmd = Command()
            cmd.stdout = MagicMock()
            cmd.handle()

            assert Traffic.objects.count() == 0

    def test_fetch_traffic_handles_invalid_data_format(self):
        from odin.apps.provider.management.commands.fetch_traffic import Command

        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "invalid_format"

        mock_driver.find_element.return_value = mock_element

        with patch(
            "odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome",
            return_value=mock_driver,
        ):
            with patch("odin.apps.provider.management.commands.fetch_traffic.WebDriverWait"):
                with patch("django.conf.settings") as mock_settings:
                    mock_settings.UNET_USERNAME = "testuser"
                    mock_settings.UNET_PASSWORD = "testpass"

                    cmd = Command()
                    cmd.stdout = MagicMock()
                    cmd.handle()

                    assert Traffic.objects.count() == 0
