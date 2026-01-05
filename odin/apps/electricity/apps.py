from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ElectricityConfig(AppConfig):
    name = "odin.apps.electricity"
    verbose_name = _("electricity")
