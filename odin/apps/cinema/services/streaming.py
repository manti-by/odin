import mimetypes
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import Http404, HttpResponse

from odin.apps.cinema.models import Video
from odin.apps.cinema.services.scanner import is_within_media_dirs
from odin.apps.cinema.services.trailers import get_trailer_path


VIDEO_CONTENT_TYPES = {
    ".avi": "video/x-msvideo",
    ".m2ts": "video/mp2t",
    ".m4v": "video/x-m4v",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",
    ".ts": "video/mp2t",
    ".webm": "video/webm",
    ".wmv": "video/x-ms-wmv",
}


def guess_content_type(path: Path) -> str:
    return (
        VIDEO_CONTENT_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    )


def accel_response(internal_uri: str, content_type: str) -> HttpResponse:
    """Tell nginx to stream a local file; Django never holds the bytes.

    nginx serves the aliased file with native HTTP Range support, which is what Media3 needs to
    seek on the TV. The `X-Accel-Redirect` header is consumed by nginx and not forwarded.
    """
    response = HttpResponse(status=200)
    response["X-Accel-Redirect"] = internal_uri
    response["Content-Type"] = content_type
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "no-cache"
    return response


def get_video_stream(video: Video) -> HttpResponse:
    """Authorize one library file and hand the absolute path to nginx.

    The resolved path is re-checked against `CINEMA_MEDIA_DIRS` on every request, so a symlink
    swapped into the share after the scan cannot expose a file outside the library.
    """
    path = Path(video.path).resolve()
    if not path.is_file() or not is_within_media_dirs(path):
        raise Http404(f"Video file is not available: {video.filename}")
    return accel_response(f"{settings.CINEMA_NGINX_MEDIA_URL}{quote(str(path))}", guess_content_type(path))


def get_trailer_stream(video: Video) -> HttpResponse:
    """Authorize the downloaded trailer; like the video stream, the absolute path goes to nginx."""
    path = get_trailer_path(video)
    if path is None:
        raise Http404(f"Video has no trailer: {video.filename}")
    resolved = path.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(Path(settings.CINEMA_TRAILERS_DIR).resolve()):
        raise Http404(f"Video has no trailer: {video.filename}")
    return accel_response(f"{settings.CINEMA_NGINX_TRAILERS_URL}{quote(str(resolved))}", guess_content_type(resolved))
