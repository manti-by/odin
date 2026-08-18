from django.core.management.base import BaseCommand

from odin.apps.boiler.services import BoilerService


class Command(BaseCommand):
    help = description = "Read Protherm Lynx 25 boiler state via ebusd."

    def handle(self, *args, **options):
        service = BoilerService()

        override = service.current_override() or "none"
        self.stdout.write(f"{'override:':<20}{override}")

        status = service.status()
        for name, note in BoilerService.STATUS_FIELDS:
            self.stdout.write(f"{name + ':':<20}{status[name]}  ({note})")
