"""
Custom clock process to handle scheduled tasks.

Scheduled tasks definitions should be in the danelex.apps.core.schedule module;
this command simply runs the scheduler - it should never need changing.
"""

from django.core.management.base import BaseCommand

from odin.apps.core.scheduler import scheduler


class Command(BaseCommand):
    help = "Runs the **BLOCKING** APScheduler."

    def handle(self, *args, **options):
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()

