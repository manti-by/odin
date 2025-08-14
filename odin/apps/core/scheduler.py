from django.conf import settings
from django.core.management import call_command

from apscheduler.schedulers.blocking import BlockingScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_rq import get_queue


queue = get_queue(name="default", is_async=settings.QUEUE_SCHEDULED_TASKS)

# NB VERY IMPORTANT - this is a blocking process, so must NEVER be
# called from anywhere other than the run_scheduled_tasks command.
scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")


@scheduler.scheduled_job("interval", minutes=30, id="update_weather")
def schedule_update_weather():
    call_command("update_weather")


@scheduler.scheduled_job("interval", minutes=5, id="update_sensors")
def schedule_update_sensors():
    call_command("update_sensors")
