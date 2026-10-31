from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CinemaConfig(AppConfig):
    name = "odin.apps.cinema"
    verbose_name = _("cinema")
