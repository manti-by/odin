from django.contrib import admin

from odin.apps.currency.models import ExchangeRate


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["currency", "rate", "scale", "date", "synced_at"]
    list_filter = ["currency", "date"]
    search_fields = ["currency"]
