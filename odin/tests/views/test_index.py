from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from odin.apps.currency.models import Currency
from odin.tests.factories import ExchangeRateFactory


@pytest.mark.django_db
@pytest.mark.views
class TestIndexView:
    @pytest.fixture(autouse=True)
    def _isolate_dist(self, tmp_path, settings):
        settings.FRONTEND_DIST_DIR = tmp_path

    def test_index__returns_spa_error_when_build_missing(self, client):
        response = client.get(reverse("index"), follow=True)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    def test_index__returns_spa_shell_when_build_exists(self, client, tmp_path):
        (tmp_path / "index.html").write_text("<html>SPA Shell</html>", encoding="utf-8")

        response = client.get(reverse("index"), follow=True)

        assert response.status_code == status.HTTP_200_OK
        assert b"SPA Shell" in response.content

    @patch("odin.apps.core.services.subprocess.run")
    def test_index__exchange_rates_trends_up_arrow(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"
        cache.clear()

        today = date.today()
        yesterday = today - timedelta(days=1)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)
        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=yesterday)

        from odin.apps.core.services import build_index_context

        context = build_index_context()
        assert context["exchange_rates_trends"]["USD"] > 0

    @patch("odin.apps.core.services.subprocess.run")
    def test_index__exchange_rates_trends_down_arrow(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"
        cache.clear()

        today = date.today()
        yesterday = today - timedelta(days=1)

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.1500"), date=today)
        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=yesterday)

        from odin.apps.core.services import build_index_context

        context = build_index_context()
        assert context["exchange_rates_trends"]["USD"] < 0

    @patch("odin.apps.core.services.subprocess.run")
    def test_index__exchange_rates_no_arrow_when_no_prior_data(self, mock_subprocess, client):
        mock_subprocess.return_value.stdout = b"active"
        cache.clear()

        today = date.today()

        ExchangeRateFactory(currency=Currency.USD, rate=Decimal("3.2500"), date=today)

        from odin.apps.core.services import build_index_context

        context = build_index_context()
        assert context["exchange_rates_trends"]["USD"] is None


@pytest.mark.django_db
@pytest.mark.views
class TestServiceWorkerView:
    @pytest.fixture(autouse=True)
    def _isolate_dist(self, tmp_path, settings):
        settings.FRONTEND_DIST_DIR = tmp_path

    def test_sw__returns_503_when_build_missing(self, client):
        response = client.get(reverse("sw"))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    def test_sw__returns_correct_content(self, client, settings):
        sw_content = 'self.addEventListener("install", () => self.skipWaiting());'
        sw_path = settings.FRONTEND_DIST_DIR / "sw.js"
        sw_path.parent.mkdir(parents=True, exist_ok=True)
        sw_path.write_text(sw_content)

        response = client.get(reverse("sw"))

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/javascript"
        assert response["Service-Worker-Allowed"] == "/"
        assert response.content.decode() == sw_content

    def test_manifest__returns_503_when_build_missing(self, client):
        response = client.get(reverse("manifest"))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    def test_manifest__returns_correct_content(self, client, settings):
        manifest_content = '{"name": "ODIN"}'
        manifest_path = settings.FRONTEND_DIST_DIR / "manifest.webmanifest"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(manifest_content)

        response = client.get(reverse("manifest"))

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/manifest+json"
        assert response.content.decode() == manifest_content
