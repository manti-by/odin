from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from odin.apps.core.services import (
    get_cached_index_context,
    update_index_context_cache,
)


logger = logging.getLogger(__name__)


def index_view(request: HttpRequest) -> HttpResponse:
    if not (context := get_cached_index_context()):
        context = update_index_context_cache()
    return render(request, "index.html", context=context)
