from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.core.management import call_command
from io import StringIO

from odin.apps.provider.management.commands.scrape_unet_traffic import Command
from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestScrapeUnetTrafficCommand:
    def test_command_creates_traffic_record_on_success(self):
        Traffic.objects.all().delete()

        with patch.object(Command, "scrape_unet_traffic", return_value=(Decimal("123.45"), "GB")):
            call_command("scrape_unet_traffic")

        assert Traffic.objects.count() == 1
        traffic = Traffic.objects.first()
        assert traffic.value == Decimal("123.45")
        assert traffic.unit == "GB"

    def test_command_handles_none_response(self):
        Traffic.objects.all().delete()

        with patch.object(Command, "scrape_unet_traffic", return_value=None):
            call_command("scrape_unet_traffic")

        assert Traffic.objects.count() == 0

    def test_command_handles_exception(self):
        with patch.object(Command, "scrape_unet_traffic", side_effect=Exception("Test error")):
            out = StringIO()
            call_command("scrape_unet_traffic", stdout=out)


@pytest.mark.django_db
class TestScrapeUnetTrafficExtraction:
    def test_extract_csrf_token_success(self):
        command = Command()
        driver = MagicMock()
        wait = MagicMock()

        csrf_input = MagicMock()
        csrf_input.get_attribute.return_value = "test_token_123"
        wait.until.return_value = csrf_input

        token = command._extract_csrf_token(driver, wait)
        assert token == "test_token_123"

    def test_extract_csrf_token_failure(self):
        command = Command()
        driver = MagicMock()
        wait = MagicMock()
        wait.until.side_effect = Exception("Element not found")

        token = command._extract_csrf_token(driver, wait)
        assert token is None

    def test_extract_traffic_data_success(self):
        command = Command()
        driver = MagicMock()
        wait = MagicMock()

        element = MagicMock()
        element.get_attribute.return_value = "GB;123.45"
        wait.until.return_value = element

        result = command._extract_traffic_data(driver, wait)
        assert result == (Decimal("123.45"), "GB")

    def test_extract_traffic_data_invalid_format(self):
        command = Command()
        driver = MagicMock()
        wait = MagicMock()

        element = MagicMock()
        element.get_attribute.return_value = "invalid_format"
        wait.until.return_value = element

        result = command._extract_traffic_data(driver, wait)
        assert result is None

    def test_extract_traffic_data_failure(self):
        command = Command()
        driver = MagicMock()
        wait = MagicMock()
        wait.until.side_effect = Exception("Element not found")

        result = command._extract_traffic_data(driver, wait)
        assert result is None
