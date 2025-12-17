from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RelaysConfig(AppConfig):
    name = "odin.apps.relays"
    verbose_name = _("relays")
