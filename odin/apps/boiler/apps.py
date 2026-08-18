from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BoilerConfig(AppConfig):
    name = "odin.apps.boiler"
    verbose_name = _("boiler")
