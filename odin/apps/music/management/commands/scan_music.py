import logging
from collections.abc import Iterable

from django.conf import settings

from command_log.management.commands import LoggedCommand
from odin.apps.music.services import update_or_create_music
from setuptools import glob
from tinytag import ParseError


logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Scan music library."

    @staticmethod
    def get_file_list() -> Iterable:
        """Return files in the gallery recursively."""
        for ext in (f"**/*.{ext}" for ext in ("flac", "mp3", "wav")):
            yield from glob.glob(f"{settings.MUSIC_PATH}/{ext.upper()}", recursive=True)
            yield from glob.glob(f"{settings.MUSIC_PATH}/{ext.lower()}", recursive=True)

    def handle(self, *args, **options):
        for file in self.get_file_list():
            try:
                music, _ = update_or_create_music(file=file)
                logger.info(f"{file}: [{music.album}] {music.artist} - {music.title} - {music.year}")
            except ParseError as e:
                logger.error(f"{file}: {e}")
