import logging
from datetime import date

import requests

from command_log.management.commands import LoggedCommand

from odin.apps.currency.models import Currency, ExchangeRate


logger = logging.getLogger(__name__)


ISO_CURRENCY_CODES = {
    Currency.USD: "840",
    Currency.EUR: "978",
    Currency.RUB: "643",
}


class Command(LoggedCommand):
    help = description = "Retrieve exchange rates from NBRB API."
    base_url = "https://api.nbrb.by/exrates/rates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Date in YYYY-MM-DD format (default: today)",
        )

    def handle(self, *args, **options):
        target_date = options.get("date")
        if target_date:
            target_date = date.fromisoformat(target_date)
        else:
            target_date = date.today()

        for currency in Currency.values:
            self.fetch_rate(currency, ISO_CURRENCY_CODES[currency], target_date)

    def fetch_rate(self, currency: str, iso_code: str, target_date: date):
        url = f"{self.base_url}/{iso_code}?parammode=1&ondate={target_date.isoformat()}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            rate = data.get("Cur_OfficialRate")
            scale = data.get("Cur_Scale", 1)

            ExchangeRate.objects.update_or_create(
                currency=currency,
                date=target_date,
                defaults={
                    "rate": rate,
                    "scale": scale,
                    "data": data,
                },
            )
            logger.info(f"{currency}: {rate} BYN for {scale} units ({target_date})")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {currency} rate: {e}")
