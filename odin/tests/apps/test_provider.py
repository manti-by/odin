from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestTrafficModel:
    def test_str(self):
        traffic = Traffic.objects.create(value=Decimal("12.345"), unit="GB")
        s = str(traffic)
        assert "12.345" in s
        assert "GB" in s


@pytest.mark.django_db
class TestFetchTrafficCommand:
    @override_settings(UNET_USERNAME="user", UNET_PASSWORD="pass")
    @patch("odin.apps.provider.management.commands.fetch_traffic.webdriver.Chrome")
    @patch("odin.apps.provider.management.commands.fetch_traffic.requests.Session")
    def test_fetch_traffic_creates_record(self, mock_session_cls, mock_chrome_cls):
        driver = MagicMock()
        mock_chrome_cls.return_value = driver

        csrf_element = MagicMock()
        csrf_element.get_attribute.return_value = "csrf-token"

        span_element = MagicMock()
        span_element.get_attribute.return_value = "GB;123.456"

        driver.find_element.side_effect = [csrf_element, span_element]
        driver.get_cookies.return_value = [{"name": "sessionid", "value": "abc"}]

        session = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        session.post.return_value = response
        mock_session_cls.return_value = session

        call_command("fetch_traffic")

        traffic = Traffic.objects.first()
        assert traffic is not None
        assert traffic.unit == "GB"
        assert traffic.value == Decimal("123.456")

    @override_settings(UNET_USERNAME="", UNET_PASSWORD="")
    def test_fetch_traffic_requires_credentials(self):
        with pytest.raises(CommandError):
            call_command("fetch_traffic")

