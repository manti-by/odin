import logging
import subprocess  # nosec B404
from decimal import Decimal

from command_log.management.commands import LoggedCommand

from odin.apps.electricity.models import VoltageLog


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Retrieve input voltage from UPS and save to database."

    def handle(self, *args, **options):
        try:
            # Run the upsc command to get voltage
            command = ["/usr/bin/upsc", "exegate@localhost", "input.voltage"]
            result = subprocess.run(command, capture_output=True, shell=False, text=True, check=True, timeout=10)  # nosec B603

            # Parse the voltage value (remove any whitespace/newlines)
            # and convert to Decimal for storage
            voltage = Decimal(result.stdout.strip())
            VoltageLog.objects.create(voltage=voltage)
            logger.info(f"Voltage logged: {voltage}V")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute upsc command: {e.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("Upsc command timed out")

        except ValueError as e:
            logger.error(f"Failed to parse voltage value: {e}")
