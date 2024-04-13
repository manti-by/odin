"""
Contains all scheduled task definitions.

This is imported into the clock management command.

"""
from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings
from django.core.management import call_command
from django_apscheduler.jobstores import DjangoJobStore
from django_rq import get_queue

queue = get_queue(name="default", is_async=settings.QUEUE_SCHEDULED_TASKS)

# NB VERY IMPORTANT - this is a blocking process, so must NEVER be
# called from anywhere other than the run_scheduled_tasks command.
scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")


# Every hour
@scheduler.scheduled_job("interval", minutes=1, id="update_sensors")
def update_sensors():
    call_command("update_sensors")


# Every day
@scheduler.scheduled_job("interval", minutes=30, id="send_sensors")
def send_sensors():
    call_command("send_sensors")
