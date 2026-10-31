import mimetypes
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import Http404, HttpResponse

from odin.apps.cinema.models import Video
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
    path = Path(video.path)
    if not path.is_file():
        raise Http404(f"Video file is not available: {video.filename}")
    return accel_response(f"{settings.CINEMA_NGINX_MEDIA_URL}{quote(str(path))}", guess_content_type(path))


def get_trailer_stream(video: Video) -> HttpResponse:
    path = get_trailer_path(video)
    if path is None or not path.is_file():
        raise Http404(f"Video has no trailer: {video.filename}")
    # `CINEMA_NGINX_TRAILERS_URL` is aliased straight to `CINEMA_TRAILERS_DIR`, so only the
    # file name goes into the internal URI.
    return accel_response(f"{settings.CINEMA_NGINX_TRAILERS_URL}{quote(path.name)}", guess_content_type(path))
