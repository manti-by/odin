import logging

from command_log.management.commands import LoggedCommand
from django.conf import settings

from odin.apps.video.services import (
    process_pending_metadata,
    process_pending_trailers,
    process_pending_translations,
    scan_library,
)


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Scan video media directories and refresh metadata and trailers."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Max videos per fetch phase (default: setting)")
        parser.add_argument("--no-translations", action="store_true", help="Skip the title translation phase")
        parser.add_argument("--no-metadata", action="store_true", help="Skip the OMDb metadata phase")
        parser.add_argument("--no-trailers", action="store_true", help="Skip the trailer download phase")

    def handle(self, *args, **options):
        stats = scan_library()
        limit = settings.VIDEO_SCAN_BATCH_SIZE if options["limit"] is None else options["limit"]

        translations = 0 if options["no_translations"] else process_pending_translations(limit)
        metadata = 0 if options["no_metadata"] else process_pending_metadata(limit)
        trailers = 0 if options["no_trailers"] else process_pending_trailers(limit)
        logger.info(
            f"Video pipeline: {stats['found']} files, {translations} translations, "
            f"{metadata} metadata, {trailers} trailers"
        )
