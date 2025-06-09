import logging

from django.http import HttpRequest
from django.shortcuts import render


logger = logging.getLogger(__name__)


def index_view(request: HttpRequest) -> str:
    context = {}
    return render(request, "index.html", context=context)
