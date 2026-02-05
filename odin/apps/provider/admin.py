from django.contrib import admin

from odin.apps.provider.models import Traffic


@admin.register(Traffic)
class TrafficAdmin(admin.ModelAdmin):
    list_display = ("value", "unit", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
    search_fields = ("unit",)
