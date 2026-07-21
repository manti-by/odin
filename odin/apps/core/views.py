from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseServerError


def _read_dist_file(filename: str, content_type: str, headers: dict[str, str] | None = None) -> HttpResponse:
    file_path = settings.FRONTEND_DIST_DIR / filename
    try:
        with open(file_path, encoding="utf-8") as f:
            response = HttpResponse(f.read(), content_type=content_type)
            if headers:
                for key, value in headers.items():
                    response[key] = value
            return response
    except OSError:
        return HttpResponseServerError(
            "<h1>Frontend build not available</h1><p>Run <code>make frontend</code> to build the SPA.</p>"
        )


def index_view(request: HttpRequest) -> HttpResponse:
    return _read_dist_file("index.html", "text/html")


def service_worker_view(request: HttpRequest) -> HttpResponse:
    return _read_dist_file(
        "sw.js",
        "application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


def manifest_view(request: HttpRequest) -> HttpResponse:
    return _read_dist_file("manifest.webmanifest", "application/manifest+json")
