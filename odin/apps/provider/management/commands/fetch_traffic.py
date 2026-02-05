from __future__ import annotations

import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from odin.apps.provider.models import Traffic


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetches traffic data from my.unet.by and stores it in the database."

    def handle(self, *args, **options) -> None:
        username = getattr(settings, "UNET_USERNAME", None)
        password = getattr(settings, "UNET_PASSWORD", None)
        if not username or not password:
            raise CommandError("UNET_USERNAME and UNET_PASSWORD must be set in Django settings.")

        options_ = Options()
        options_.add_argument("--headless=new")
        options_.add_argument("--no-sandbox")
        options_.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options_)
        try:
            login_url = "https://my.unet.by/login"
            driver.get(login_url)

            csrf_input = driver.find_element(By.NAME, "_csrf_token")
            csrf_token = csrf_input.get_attribute("value")

            cookies = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}

            session = requests.Session()
            for name, value in cookies.items():
                session.cookies.set(name, value)

            payload = {
                "_csrf_token": csrf_token,
                "username": username,
                "password": password,
            }

            response = session.post(login_url, data=payload, timeout=30)
            response.raise_for_status()

            driver.get("https://my.unet.by/")

            span = driver.find_element(By.CSS_SELECTOR, "#unet-general-info-box-infobox span[data-units]")
            data_units = span.get_attribute("data-units")
            if not data_units or ";" not in data_units:
                raise CommandError(f"Unexpected data-units format: {data_units}")

            unit, value_str = data_units.split(";", 1)
            value = Decimal(value_str.strip())

            Traffic.objects.create(value=value, unit=unit.strip(), created_at=timezone.now())
            logger.info("Traffic data saved: %s %s", value, unit)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to fetch traffic data: %s", exc)
            raise CommandError(f"Failed to fetch traffic data: {exc}") from exc
        finally:
            driver.quit()

