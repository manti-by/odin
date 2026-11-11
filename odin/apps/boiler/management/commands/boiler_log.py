from django.core.management.base import BaseCommand

from odin.apps.boiler.services.log import log_boiler_status


class Command(BaseCommand):
    help = description = "Store a snapshot of the current boiler mode and setpoints."

    def handle(self, *args, **options):
        entry = log_boiler_status()

        self.stdout.write(self.style.SUCCESS(f"logged {entry}"))
