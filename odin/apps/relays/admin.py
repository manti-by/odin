from django.contrib import admin

from .models import Relay


@admin.register(Relay)
class RelayAdmin(admin.ModelAdmin):
    list_display = ("relay_id", "name", "type", "is_active", "updated_at", "created_at")
    list_filter = ("type",)
