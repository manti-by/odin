from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseServerError


def index_view(request: HttpRequest) -> HttpResponse:
    """Serve the built React SPA shell."""
    try:
        with open(settings.FRONTEND_DIST_DIR / "index.html", encoding="utf-8") as f:
            return HttpResponse(f.read())
    except OSError:
        return HttpResponseServerError(
            "<h1>Frontend build not available</h1><p>Run <code>make frontend</code> to build the SPA.</p>"
        )
