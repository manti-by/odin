import os
import re
from datetime import datetime
from pathlib import Path

from django.conf import settings

import pytz
from odin.apps.music.models import Music
from tinytag import TinyTag


def update_or_create_music(file: str) -> tuple[Music, bool]:
    file = Path(file).resolve()
    tags = TinyTag.get(file)
    created_at = datetime.fromtimestamp(file.stat().st_ctime, tz=pytz.UTC)

    year = None
    if tags.year:
        try:
            year = int(tags.year)
        except ValueError:
            pass
        if match := re.match(r"(?P<year>\d)-\d-\d", tags.year):
            year = match.group("year")

    artist, title, album = tags.artist, tags.title, tags.album
    if not artist or not title:
        if match := re.match(r"(?P<artist>[\w\s.]*)\s-\s(?P<title>[\w\s.,()]*).*", file.name):
            artist, title = match.group("artist").strip(), match.group("title").strip()

    if not artist or not title:
        if match := re.match(r"Manti_(?P<title>[\w\s]*).*", file.name):
            artist, title = "Manti", match.group("title").replace("_", " ").strip()

    if not album:
        try:
            album = file.parents[0].name
        except IndexError:
            pass

    filesize = tags.filesize
    if not tags.filesize:
        filesize = os.path.getsize(file)

    file_name = str(file).replace(settings.MUSIC_PATH, "")
    return Music.objects.update_or_create(
        file=file_name,
        defaults={
            "meta": {
                "filesize": filesize,
                "duration": tags.duration,
                "channels": tags.channels,
                "bitrate": tags.bitrate,
                "samplerate": tags.samplerate,
                "mtime": file.stat().st_mtime,
                "atime": file.stat().st_atime,
                "ctime": file.stat().st_ctime,
            },
            "album": album,
            "artist": artist,
            "title": title,
            "genre": tags.genre,
            "year": year,
            "has_cover": bool(tags.images.any),
            "created_at": created_at,
        },
    )
