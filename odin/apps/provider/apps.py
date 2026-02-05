from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProviderConfig(AppConfig):
    name = "odin.apps.provider"
    verbose_name = _("provider")
