import logging
from decimal import Decimal

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from command_log.management.commands import LoggedCommand
from django.conf import settings

from odin.apps.provider.models import Traffic


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Scrape traffic information from UNET provider."

    def handle(self, *args, **options):
        try:
            traffic_data = self.scrape_unet_traffic()
            if traffic_data:
                value, unit = traffic_data
                Traffic.objects.create(value=value, unit=unit)
                logger.info(f"Traffic data saved: {value} {unit}")
            else:
                logger.warning("Failed to scrape traffic data")
        except Exception as e:
            logger.error(f"Error scraping UNET traffic: {e}")

    def scrape_unet_traffic(self) -> tuple[Decimal, str] | None:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--headless")

        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get("https://my.unet.by/login")
            wait = WebDriverWait(driver, 10)

            csrf_token = self._extract_csrf_token(driver, wait)
            if not csrf_token:
                logger.error("CSRF token not found")
                return None

            self._login(driver, wait, csrf_token)

            traffic_data = self._extract_traffic_data(driver, wait)
            return traffic_data
        finally:
            driver.quit()

    def _extract_csrf_token(self, driver, wait) -> str | None:
        try:
            csrf_input = wait.until(EC.presence_of_element_located((By.NAME, "_csrf_token")))
            return csrf_input.get_attribute("value")
        except Exception as e:
            logger.error(f"Failed to extract CSRF token: {e}")
            return None

    def _login(self, driver, wait, csrf_token: str) -> None:
        username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password_input = driver.find_element(By.NAME, "password")

        username_input.send_keys(settings.UNET_USERNAME)
        password_input.send_keys(settings.UNET_PASSWORD)

        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()

        wait.until(EC.presence_of_element_located((By.ID, "unet-general-info-box-infobox")))

    def _extract_traffic_data(self, driver, wait) -> tuple[Decimal, str] | None:
        try:
            element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#unet-general-info-box-infobox span"))
            )
            data_units = element.get_attribute("data-units")

            if not data_units or ";" not in data_units:
                logger.error(f"Invalid data format: {data_units}")
                return None

            unit, value = data_units.split(";", 1)
            return Decimal(value.strip()), unit.strip()
        except Exception as e:
            logger.error(f"Failed to extract traffic data: {e}")
            return None
