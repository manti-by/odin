#!/usr/bin/env python
"""Management command to fetch UNET traffic data using Selenium."""

from __future__ import annotations

import logging
import time
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from odin.apps.provider.models import Traffic

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch UNET traffic data using Selenium web driver"

    def add_arguments(self, parser):
        parser.add_argument(
            "--headless",
            action="store_true",
            help="Run browser in headless mode",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Timeout for web driver operations in seconds",
        )

    def handle(self, *args, **options):
        headless = options["headless"]
        timeout = options["timeout"]

        if not settings.UNET_USERNAME or not settings.UNET_PASSWORD:
            logger.error("UNET_USERNAME and UNET_PASSWORD must be set in environment")
            return

        try:
            # Initialize Selenium WebDriver
            chrome_options = webdriver.ChromeOptions()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")

            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(timeout)

            # Navigate to UNET login page
            logger.info("Navigating to UNET login page")
            driver.get("https://my.unet.by/login")

            # Wait for login form to load
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.NAME, "_csrf_token"))
            )

            # Extract CSRF token
            csrf_token = driver.find_element(By.NAME, "_csrf_token").get_attribute("value")
            logger.info(f"Extracted CSRF token: {csrf_token[:10]}...")

            # Fill login form and submit
            username_field = driver.find_element(By.NAME, "username")
            password_field = driver.find_element(By.NAME, "password")
            csrf_field = driver.find_element(By.NAME, "_csrf_token")

            username_field.send_keys(settings.UNET_USERNAME)
            password_field.send_keys(settings.UNET_PASSWORD)
            csrf_field.send_keys(csrf_token)

            # Submit the form
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            # Wait for login to complete and redirect to dashboard
            logger.info("Waiting for login to complete...")
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "unet-general-info-box-infobox"))
            )

            # Extract traffic data
            logger.info("Extracting traffic data...")
            traffic_span = driver.find_element(
                By.CSS_SELECTOR, "#unet-general-info-box-infobox span[data-units]"
            )
            data_units = traffic_span.get_attribute("data-units")

            if not data_units:
                logger.error("No traffic data found")
                return

            # Parse data-units format (unit;value)
            unit, value_str = data_units.split(";")
            value = Decimal(value_str)

            logger.info(f"Traffic data: {value} {unit}")

            # Save to database
            Traffic.objects.create(value=value, unit=unit)
            logger.info("Traffic data saved successfully")

        except NoSuchElementException as e:
            logger.error(f"Element not found: {e}")
        except TimeoutException as e:
            logger.error(f"Timeout waiting for element: {e}")
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            try:
                if "driver" in locals():
                    driver.quit()
                    logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")