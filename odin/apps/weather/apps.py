from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WeatherConfig(AppConfig):
    name = "odin.apps.weather"
    verbose_name = _("weather")
