from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProviderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "odin.apps.provider"
    verbose_name = _("Provider")
