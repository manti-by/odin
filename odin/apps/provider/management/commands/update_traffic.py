import logging
import re
from decimal import Decimal

from command_log.management.commands import LoggedCommand
from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from odin.apps.provider.models import Traffic


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Scrape traffic data from unet.by portal."

    def handle(self, *args, **options):
        username = settings.UNET_USERNAME
        password = settings.UNET_PASSWORD

        if not username or not password:
            logger.error("UNET_USERNAME and UNET_PASSWORD settings must be configured")
            return

        driver = None
        try:
            driver = webdriver.Chrome()
            driver.get("https://my.unet.by/login")

            # Wait for login form and enter credentials
            wait = WebDriverWait(driver, 10)
            username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_field = driver.find_element(By.NAME, "password")
            login_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")

            username_field.send_keys(username)
            password_field.send_keys(password)
            login_button.click()

            # Wait for the main page to load
            wait.until(EC.presence_of_element_located((By.ID, "unet-general-info-box-infobox")))

            # Get traffic info from the data-units attribute
            traffic_element = driver.find_element(By.CSS_SELECTOR, "#unet-general-info-box-infobox span")
            data_units = traffic_element.get_attribute("data-units")

            if data_units:
                # Parse format "unit;value"
                match = re.match(r"([^;]+);([0-9.]+)", data_units.strip())
                if match:
                    unit = match.group(1).strip()
                    value = Decimal(match.group(2))

                    # Save to database
                    traffic = Traffic.objects.create(value=value, unit=unit)
                    logger.info(f"Saved traffic data: {value} {unit}")
                else:
                    logger.error(f"Failed to parse data-units format: {data_units}")
            else:
                logger.error("data-units attribute not found")

        except TimeoutException as e:
            logger.error(f"Timeout waiting for page elements: {e}")
        except Exception as e:
            logger.error(f"Error scraping traffic data: {e}")
        finally:
            if driver:
                driver.quit()
