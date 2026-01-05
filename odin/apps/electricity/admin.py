from django.contrib import admin

from odin.apps.electricity.models import VoltageLog


@admin.register(VoltageLog)
class VoltageLogAdmin(admin.ModelAdmin):
    list_display = ("voltage", "created_at")
    search_fields = ("voltage",)
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
