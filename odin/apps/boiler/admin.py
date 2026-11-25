from django.contrib import admin

from odin.apps.boiler.models import BoilerLog


@admin.register(BoilerLog)
class BoilerLogAdmin(admin.ModelAdmin):
    list_display = ("hcmode", "flow_temp", "hwc_temp", "created_at")
    search_fields = ("hcmode",)
    list_filter = ("hcmode", "created_at")
