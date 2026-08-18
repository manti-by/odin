from django.core.management.base import BaseCommand, CommandError

from odin.apps.boiler.services import BoilerService, EbusdError


class Command(BaseCommand):
    help = description = "Set Protherm Lynx 25 boiler mode and temperatures via ebusd (Vaillant BAI SetMode)."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        boiling = subparsers.add_parser("boiling", help="hot water only (SetMode water)")
        boiling.add_argument("hwc_temp", type=int, help="hot-water/tank setpoint, °C")

        heating = subparsers.add_parser("heating", help="heating only (SetMode heat); hot water uses panel setpoint")
        heating.add_argument("flow_temp", type=int, help="heating flow setpoint for floors/radiators, °C")

        mixed = subparsers.add_parser("mixed", help="heating + hot water (SetMode auto)")
        mixed.add_argument("flow_temp", type=int, help="heating flow setpoint, °C")
        mixed.add_argument("hwc_temp", type=int, help="hot-water/tank setpoint, °C")

        subparsers.add_parser("off", help="both circuits off (SetMode off)")
        subparsers.add_parser("panel", help="drop the override; boiler panel takes back control")
        subparsers.add_parser("refresh", help="re-send the last override (used by boiler-refresh.timer)")

    def handle(self, *args, **options):
        service = BoilerService()
        action = options["action"]

        try:
            if action == "panel":
                service.clear_override()
                self.stdout.write("override cleared; boiler falls back to panel settings within a few minutes")
                return
            if action == "refresh":
                sent = service.refresh()
                if sent is None:
                    self.stdout.write("no override active")
                    return
            elif action == "boiling":
                sent = service.set_boiling(options["hwc_temp"])
            elif action == "heating":
                sent = service.set_heating(options["flow_temp"])
            elif action == "mixed":
                sent = service.set_mixed(options["flow_temp"], options["hwc_temp"])
            else:  # off
                sent = service.set_off()
        except (ValueError, EbusdError) as e:
            raise CommandError(str(e)) from e

        self.stdout.write(self.style.SUCCESS(f"sent SetMode {sent}"))
