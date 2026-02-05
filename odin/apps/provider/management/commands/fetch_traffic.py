import logging
from decimal import Decimal

from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from command_log.management.commands import LoggedCommand

from odin.apps.provider.models import Traffic

logger = logging.getLogger(__name__)

UNET_LOGIN_URL = "https://my.unet.by/login"
UNET_INFOBOX_SELECTOR = "#unet-general-info-box-infobox span"
DATA_UNITS_ATTRIBUTE = "data-units"


class Command(LoggedCommand):
    help = description = "Fetch traffic data from Unet.by"

    def add_arguments(self, parser):
        parser.add_argument(
            "--headless",
            action="store_true",
            default=True,
            help="Run browser in headless mode",
        )
        parser.add_argument(
            "--no-headless",
            action="store_false",
            dest="headless",
            help="Run browser in visible mode (for debugging)",
        )

    def handle(self, *args, **options):
        headless = options["headless"]
        username = settings.UNET_USERNAME
        password = settings.UNET_PASSWORD

        if not username or not password:
            logger.error("UNET_USERNAME and UNET_PASSWORD must be set in settings")
            return

        driver = None
        try:
            driver = self._create_driver(headless=headless)
            driver.get(UNET_LOGIN_URL)

            self._login(driver, username, password)

            data_units = self._extract_traffic_data(driver)

            unit, value = self._parse_data_units(data_units)

            traffic = Traffic.objects.create(value=value, unit=unit)

            logger.info(f"Created traffic record: {traffic}")

        except Exception as e:
            logger.error(f"Failed to fetch traffic data: {e}")

        finally:
            if driver:
                driver.quit()

    def _create_driver(self, headless: bool = True) -> webdriver.Chrome:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        return webdriver.Chrome(options=chrome_options)

    def _login(self, driver: webdriver.Chrome, username: str, password: str) -> None:
        wait = WebDriverWait(driver, 10)

        username_field = wait.until(
            ec.presence_of_element_located((By.NAME, "login")),
        )
        username_field.send_keys(username)

        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(password)

        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, UNET_INFOBOX_SELECTOR)))

    def _extract_traffic_data(self, driver: webdriver.Chrome) -> str:
        wait = WebDriverWait(driver, 10)

        infobox_span = wait.until(
            ec.presence_of_element_located((By.CSS_SELECTOR, UNET_INFOBOX_SELECTOR)),
        )

        data_units = infobox_span.get_attribute(DATA_UNITS_ATTRIBUTE)

        if not data_units:
            raise ValueError(f"Attribute {DATA_UNITS_ATTRIBUTE} not found on element")

        return data_units

    def _parse_data_units(self, data_units: str) -> tuple[str, Decimal]:
        parts = data_units.split(";")

        if len(parts) != 2:
            raise ValueError(f"Invalid data-units format: {data_units}")

        unit = parts[0].strip()
        value = Decimal(parts[1].strip())

        return unit, value
