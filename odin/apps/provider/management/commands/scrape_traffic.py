import logging
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from odin.apps.provider.models import Traffic

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrape traffic data from UNET"

    def handle(self, *args, **options):
        driver = webdriver.Chrome()
        try:
            driver.get("https://my.unet.by/login")

            csrf_token = driver.find_element(By.NAME, "_csrf_token").get_attribute("value")

            username = settings.UNET_USERNAME
            password = settings.UNET_PASSWORD

            driver.find_element(By.ID, "username").send_keys(username)
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#unet-general-info-box-infobox span"))
            )

            element = driver.find_element(By.CSS_SELECTOR, "#unet-general-info-box-infobox span")
            data_units = element.get_attribute("data-units")

            unit, value_str = data_units.split(";")
            value = Decimal(value_str.replace(",", "."))

            Traffic.objects.create(value=value, unit=unit)
            logger.info(f"Saved traffic: {value} {unit}")

        except Exception as e:
            logger.error(f"Error scraping traffic: {e}")
        finally:
            driver.quit()
