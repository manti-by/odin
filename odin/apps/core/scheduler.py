from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore
from django_rq import get_queue

from odin.apps.core.webpush import send_push_notification_to_admins


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


@scheduler.scheduled_job("interval", minutes=1, id="update_index_context")
def schedule_update_index_context():
    from odin.apps.core.services import update_index_context_cache

    context = update_index_context_cache()
    if not context["home_sensors_is_alive"] or not context["boiler_sensors_is_alive"]:
        send_push_notification_to_admins(title="Sensors error", body="One or more sensors are not responding.")


@scheduler.scheduled_job("interval", hours=4, id="update_exchange_rates")
def schedule_update_exchange_rates():
    call_command("update_exchange_rates")


@scheduler.scheduled_job("interval", minutes=15, id="fetch_traffic")
def schedule_fetch_traffic():
    call_command("fetch_traffic")
