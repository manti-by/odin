import logging
import subprocess  # nosec

from django.conf import settings


logger = logging.getLogger(__name__)


def systemd_status() -> dict[str, dict]:
    if settings.DEBUG:
        return {"scheduler.service": {"status": "active"}, "worker.service": {"error": "DEBUG error message"}}

    result = {}
    for service in ["scheduler.service", "worker.service"]:
        try:
            status = subprocess.run(["/usr/bin/systemctl", "is-active", service], capture_output=True, check=True)  # nosec
            result[service] = {"status": status.stdout.decode().strip()}
        except subprocess.CalledProcessError as e:
            logger.error(f"Cannot get status for {service}: {e}")
            result[service] = {"error": str(e)}
    return result
