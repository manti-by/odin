from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from odin.apps.provider.models import Traffic


@admin.register(Traffic)
class TrafficAdmin(admin.ModelAdmin):
    list_display = ("value", "unit", "created_at")
    list_filter = ("unit", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("value", "unit")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
