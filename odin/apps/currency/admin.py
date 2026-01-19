from django.contrib import admin


@admin.register
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["currency", "rate", "scale", "date", "synced_at"]
    list_filter = ["currency", "date"]
    search_fields = ["currency"]
