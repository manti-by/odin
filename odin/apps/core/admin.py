from django.contrib import admin

from .models import Device, Log


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "browser", "is_active", "created_at", "updated_at")
    list_filter = ("browser", "is_active", "created_at")
    search_fields = ("subscription",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ("levelname", "filename", "name", "msg", "asctime")
    search_fields = ("msg",)
    list_filter = ("levelname", "filename", "asctime")
