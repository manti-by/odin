from __future__ import annotations

import logging
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from django.conf import settings
from django.core.management.base import BaseCommand

from odin.apps.provider.models import Traffic


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch traffic data from UNET and save to database"

    def handle(self, *args: Any, **options: Any) -> None:
        username = settings.UNET_USERNAME
        password = settings.UNET_PASSWORD

        if not username or not password:
            logger.error("UNET_USERNAME or UNET_PASSWORD not set in settings")
            return

        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")  # Use "--headless=new" for Chrome 109+
            chrome_options.add_argument("--window-size=1920,1080")  # Set a consistent viewport size

            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://my.unet.by/login")

            WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.NAME, "username")))

            username_field = driver.find_element(By.NAME, "username")
            username_field.send_keys(username)

            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(password)

            login_button = driver.find_element(By.XPATH, "//input[@type='submit']")
            login_button.click()

            WebDriverWait(driver, 10).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "#unet-general-info-box-infobox span")
                )
            )

            element = driver.find_element(By.CSS_SELECTOR, "#unet-general-info-box-infobox span")
            data_units = element.get_attribute("data-units")

            if data_units and ";" in data_units:
                unit, value = data_units.split(";", 1)
                traffic = Traffic.objects.create(value=value, unit=unit.strip())
                logger.info(f"Saved traffic data: {traffic}")
            else:
                logger.warning(f"Unexpected data-units format: {data_units}")

            driver.quit()

        except Exception as e:
            logger.exception(f"Error fetching traffic data: {e}")
