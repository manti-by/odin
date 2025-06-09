from django.contrib import admin

from odin.apps.weather.models import Weather


@admin.register(Weather)
class WeatherAdmin(admin.ModelAdmin):
    list_display = ("external_id", "provider", "period", "synced_at")
    search_fields = ("period",)
    list_filter = ("provider", "period")
