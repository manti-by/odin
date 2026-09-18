import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore
from django_rq import get_queue


logger = logging.getLogger(__name__)

queue = get_queue(name="default", is_async=settings.QUEUE_SCHEDULED_TASKS)

# NB VERY IMPORTANT - this is a blocking process, so must NEVER be
# called from anywhere other than the run_scheduled_tasks command.
scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")


@scheduler.scheduled_job("interval", minutes=30, id="update_weather")
def schedule_update_weather():
    call_command("update_weather")


@scheduler.scheduled_job("interval", minutes=5, id="update_voltage")
def schedule_update_voltage():
    call_command("update_voltage")


@scheduler.scheduled_job("interval", hours=4, id="update_exchange_rates")
def schedule_update_exchange_rates():
    call_command("update_exchange_rates")


@scheduler.scheduled_job("interval", minutes=15, id="fetch_traffic")
def schedule_fetch_traffic():
    call_command("fetch_traffic")


@scheduler.scheduled_job("interval", minutes=5, id="update_boiler_mode", max_instances=1)
def schedule_update_boiler_mode():
    """React to pump/weather changes within minutes.

    Uses an interval trigger so the fire time is relative to the previous run:
    DST transitions in ``settings.TIME_ZONE`` shift the wall-clock time but
    never skip or duplicate a tick. ``max_instances=1`` prevents overlap, and
    the ebusd write is additionally serialized by ``BOILER_LOCK_FILE``. While
    the weekly boiling override (Sat 01:00-02:00) is active the controller
    skips, so the scheduled hot-water cycle is never fought.
    ``scheduled_job`` always registers with ``replace_existing=True``, so a
    scheduler restart picks up the latest definition.

    The controller must never take down the blocking scheduler process, so any
    error (ebusd unavailable, DB read failure, unexpected mode) is logged and
    swallowed; the next tick retries.
    """
    from odin.apps.boiler.services.controller import run_boiler_mode_controller

    try:
        run_boiler_mode_controller()
    except Exception:
        logger.exception("Boiler mode controller failed")
