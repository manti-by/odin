from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MusicConfig(AppConfig):
    name = "odin.apps.music"
    verbose_name = _("music")
